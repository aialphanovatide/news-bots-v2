from flask import Blueprint, jsonify, request
from config import Blacklist, Category, Bot, Keyword, Site
from app.utils.index import fetch_news_links

activate_bots_bp = Blueprint(
    'activate_bots_bp', __name__,
    template_folder='templates',
    static_folder='static'
)


@activate_bots_bp.route('/activate_all_bots', methods=['POST'])
async def activate_all_bots():
    try:
        categories = Category.query.all()
        all_sites = []

        for category in categories:
            bots = Bot.query.filter_by(category_id=category.id).all()
            for bot in bots:
                site = Site.query.filter_by(bot_id=bot.id).first()
                if not site or not site.url:
                    continue  
                bot_site = site.url
                bot_keywords = Keyword.query.filter_by(bot_id=bot.id).all()
                bot_blacklist = Blacklist.query.filter_by(bot_id=bot.id).all()
                keywords = [keyword.name for keyword in bot_keywords]
                blacklist = [blacklist.name for blacklist in bot_blacklist]

                # Aquí pasamos el ID del bot a la función fetch_news_links
                bot_id = bot.id
                await fetch_news_links(url=bot_site, keywords=keywords, blacklist=blacklist, category_id=category.id, bot_id=bot_id)
        return jsonify({'message': 'All bots activated and links fetched successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@activate_bots_bp.route('/activate_bots_by_category', methods=['POST'])
async def activate_bots_by_category():
    try:
        category_name = request.json.get('category_name')
        if not category_name:
            return jsonify({'error': 'Category name is required'}), 400

        category = Category.query.filter_by(name=category_name).first()
        if not category:
            return jsonify({'error': 'Category not found'}), 404

        bots = Bot.query.filter_by(category_id=category.id).all()
        for bot in bots:
            site = Site.query.filter_by(bot_id=bot.id).first()
            if not site or not site.url:
                continue 
            bot_site = site.url
            bot_keywords = Keyword.query.filter_by(bot_id=bot.id).all()
            bot_blacklist = Blacklist.query.filter_by(bot_id=bot.id).all()
            keywords = [keyword.name for keyword in bot_keywords]
            blacklist = [blacklist.name for blacklist in bot_blacklist]
            bot_id = bot.id
            await fetch_news_links(url=bot_site, keywords=keywords, blacklist=blacklist, category_id=category.id, bot_id=bot_id)

        return jsonify({'message': 'Bots activated and links fetched successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
