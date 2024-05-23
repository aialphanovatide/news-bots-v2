from flask import Blueprint, jsonify, request
from config import Blacklist, Category, Bot, Site, db
from app.utils.index import fetch_news_links
from scheduler_config_1 import scheduler


activate_bots_bp = Blueprint(
    'activate_bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Function to be scheduled
def scheduled_job(bot_site, bot_name, bot_blacklist, category_id, bot_id):
    with scheduler.app.app_context(): 
        fetch_news_links(
            url=bot_site,
            bot_name=bot_name,
            blacklist=bot_blacklist,
            category_id=category_id,
            bot_id=bot_id
        )


# Activate all categories
@activate_bots_bp.route('/activate_all_categories', methods=['POST'])
async def activate_all_bots():
    response = {'data': None, 'error': None, 'success': False}
    try:
        # Fetch all categories from the database
        categories = Category.query.all()
        if not categories:
            response['error'] = 'No categories found'
            return jsonify(response), 404

        for category in categories:
            category_id = category.id
            category_interval = category.time_interval

            # Fetch all bots associated with the current category
            bots = Bot.query.filter_by(category_id=category_id).all()

            for bot in bots:
                # Fetch the associated site for the bot
                site = Site.query.filter_by(bot_id=bot.id).first()
                if not site or not site.url:
                    continue  # Skip if no site or site URL is found

                # Prepare the necessary data for the bot
                bot_site = site.url
                bot_blacklist = [bl.name for bl in Blacklist.query.filter_by(bot_id=bot.id).all()]
                bot_id = bot.id
                bot_name = bot.name


                # Schedule job for bot
                scheduler.add_job(
                    id=str(bot_name), 
                    func=scheduled_job,
                    name=bot_name, 
                    replace_existing=True,
                    args=[bot_site, bot_name, bot_blacklist, category.id, bot_id],
                    trigger='interval', 
                    minutes=category_interval
                    )

            # Set category as active
            category.is_active = True
            db.session.commit()

        response['message'] = 'All categories activated'
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        db.session.rollback()
        response['error'] = f"Error activating all bots: {e}"
        return jsonify(response), 500

# Activate a single category
@activate_bots_bp.route('/activate_category', methods=['POST'])
def activate_bots_by_category():
    response = {'data': None, 'error': None, 'success': False}
  
    try:
        # Get the category name from the request JSON
        category_name = request.json.get('category_name')
        if not category_name:
            response['error'] = 'Category name is required'
            return jsonify(response), 400

        # Fetch the category from the database
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            response['error'] = 'Category not found'
            return jsonify(response), 404

        # Check if the category is already active
        category_interval = category.time_interval
        if category.is_active:
            response['message'] = f"{category_name} category is already active"
            return jsonify(response), 200

        # Fetch all bots associated with the category
        bots = Bot.query.filter_by(category_id=category.id).all()

        for bot in bots:
            # Fetch the associated site for the bot
            site = Site.query.filter_by(bot_id=bot.id).first()
            if not site or not site.url:
                continue  # Skip if no site or site URL is found

            # Prepare the necessary data for the bot
            bot_site = site.url
            bot_blacklist = [bl.name for bl in Blacklist.query.filter_by(bot_id=bot.id).all()]
            bot_id = bot.id
            bot_name = bot.name

            scheduler.add_job(
                id=str(bot_name), 
                func=scheduled_job,
                name=bot_name, 
                replace_existing=True,
                args=[bot_site, bot_name, bot_blacklist, category.id, bot_id],
                trigger='interval', 
                minutes=1
                )
            
        # Set category as active
        category.is_active = True
        db.session.commit()

        response['message'] = f'{category_name} category was activated successfully'
        response['success'] = True
        return jsonify(response), 200

    except Exception as e:
        db.session.rollback()
        response['error'] = f"Error activating bots for category '{category_name}': {e}"
        return jsonify(response), 500



# Endpoint to list all scheduled jobs
@activate_bots_bp.route('/jobs', methods=['GET'])
def list_jobs():
    jobs = scheduler.get_jobs()
    job_list = [{'id': job.id, 'name': job.name, 'next_run_time': job.next_run_time} for job in jobs]
    return jsonify(job_list)