from flask import Blueprint, jsonify, request
from config import Blacklist, Category, Bot, Keyword, Site, db
from app.utils.index import fetch_news_links
from scheduler_config import scheduler

activate_bots_bp = Blueprint(
    'activate_bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

# Change status of the category field is_active=True
# Activates all bots
@activate_bots_bp.route('/activate_all_bots', methods=['POST'])
async def activate_all_bots():
    try:
        # Fetch all categories from the database
        categories = Category.query.all()
        if not categories:
            return jsonify({'error': 'No categories found'}), 404

        for category in categories:
            # Set category as active
            category.is_active = True
            db.session.commit()  # Commit the change to the database

            # Fetch all bots associated with the current category
            bots = Bot.query.filter_by(category_id=category.id).all()
            for bot in bots:
                # Fetch the associated site for the bot
                site = Site.query.filter_by(bot_id=bot.id).first()
                if not site or not site.url:
                    continue  # Skip if no site or site URL is found

                # Prepare the necessary data for the bot
                bot_site = site.url
                bot_blacklist = Blacklist.query.filter_by(bot_id=bot.id).all()
                blacklist = [bl.name for bl in bot_blacklist]
                bot_id = bot.id
                bot_name = bot.name

                # Perform fetch news links
                await fetch_news_links(
                    url=bot_site,
                    blacklist=blacklist,
                    bot_name=bot_name,
                    category_id=category.id,
                    bot_id=bot_id
                )

        return jsonify({'message': 'All bots activated'}), 200

    except Exception as e:
        return jsonify({'error': f"Error activating all bots: {e}"}), 500


# Change status of the category field is_active=True
# Activate all the bots of a category
@activate_bots_bp.route('/activate_bots_by_category', methods=['POST'])
async def activate_bots_by_category():
    try:
        # Get the category name from the request JSON
        category_name = request.json.get('category_name')
        if not category_name:
            return jsonify({'error': 'Category name is required'}), 400

        # Fetch the category from the database
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            return jsonify({'error': 'Category not found'}), 404

        # Fetch all bots associated with the category
        category_id=category.id
        bots = Bot.query.filter_by(category_id=category_id).all()


        for bot in bots:
            # Fetch the associated site for the bot
            site = Site.query.filter_by(bot_id=bot.id).first()
            if not site or not site.url:
                continue  # Skip if no site or site URL is found

            # Prepare the necessary data for the bot
            bot_site = site.url
            bot_blacklist = Blacklist.query.filter_by(bot_id=bot.id).all()
            blacklist = [bl.name for bl in bot_blacklist]
            bot_id = bot.id
            bot_name = bot.name

            print('bot_id', bot_id)
            print('bot_id', type(bot_id))

            # # Perform the asynchronous task to fetch news links
            # res = await fetch_news_links(
            #     url=bot_site,
            #     bot_name=bot_name,
            #     blacklist=blacklist,
            #     category_id=category.id,
            #     bot_id=bot_id
            # )
            # print(f'\n{bot_name} RESULTS: ', res)
            
            scheduler.add_job(fetch_news_links, 'interval', 
                                    hours=category.time_interval, 
                                    id=str(bot_id), 
                                    name=bot_name,
                                    replace_existing=True, 
                                    args=[bot_site, bot_name, blacklist, category_id, bot_id], 
                                    max_instances=2
                                    )
            

        # Set category as active
        category.is_active = True
        db.session.commit()

        return jsonify({'message': f'{category_name} category was activated successfully'}), 200

    except Exception as e:
        return jsonify({'error': f"Error activating bots for category '{category_name}': {e}"}), 500
