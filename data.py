from config import Site, db, Category, Bot


def initialize_categories():
    try:
        # Check if categories already exist
        if db.session.query(Category).count() == 0:
            # No categories found, proceed to insert fixed data
            categories_data = [
                {'id': 1, 'name': 'bitcoin', 'alias': 'Bitcoin', 'time_interval': 50, 'is_active': False, 'border_color': '#FC5404', 'icon': '/static/topmenu_icons_resize/bitcoin.png', 'created_at': '2024-03-08 14:34:11.648686'},
                {'id': 2, 'name': 'ethereum', 'alias': 'Ethereum', 'time_interval': 50, 'is_active': False, 'border_color': '#325C86', 'icon': '/static/topmenu_icons_resize/ethereum.png', 'created_at': '2024-03-08 14:34:11.777763'},
                {'id': 3, 'name': 'hacks', 'alias': 'Hacks', 'time_interval': 50, 'is_active': False, 'border_color': '#325C86', 'icon': '/static/topmenu_icons_resize/baseblock.png', 'created_at': '2024-03-08 14:34:11.913586'},
                {'id': 4, 'name': 'lsd', 'alias': 'Lsd', 'time_interval': 50, 'is_active': False, 'border_color': '#FFC53C', 'icon': '/static/topmenu_icons_resize/lsds.png', 'created_at': '2024-03-08 14:34:11.97669'},
                {'id': 5, 'name': 'layer 0', 'alias': 'RootLink', 'time_interval': 50, 'is_active': False, 'border_color': '#802291', 'icon': '/static/topmenu_icons_resize/rootlink.png', 'created_at': '2024-03-08 14:34:12.19776'},
                {'id': 6, 'name': 'layer 1 lmc', 'alias': 'BaseBlock', 'time_interval': 50, 'is_active': False, 'border_color': '#0B84CE', 'icon': '/static/topmenu_icons_resize/baseblock.png', 'created_at': '2024-03-08 14:34:12.465627'},
                {'id': 7, 'name': 'layer 1 mmc', 'alias': 'CoreChain', 'time_interval': 50, 'is_active': False, 'border_color': '#FDE74B', 'icon': '/static/topmenu_icons_resize/corechain.png', 'created_at': '2024-03-08 14:34:12.911012'},
                {'id': 8, 'name': 'layer 2', 'alias': 'BoostLayer', 'time_interval': 50, 'is_active': False, 'border_color': '#5BD83D', 'icon': '/static/topmenu_icons_resize/boostlayer.png', 'created_at': '2024-03-08 14:34:13.259544'},
                {'id': 9, 'name': 'cross border payments', 'alias': 'X Payments', 'time_interval': 50, 'is_active': False, 'border_color': '#51DD8C', 'icon': '/static/topmenu_icons_resize/x_payments.png', 'created_at': '2024-03-08 14:34:13.992851'},
                {'id': 10, 'name': 'defip', 'alias': 'CycleSwap', 'time_interval': 50, 'is_active': False, 'border_color': '#20CBDD', 'icon': '/static/topmenu_icons_resize/cycle_swap.png', 'created_at': '2024-03-08 14:34:14.27125'},
                {'id': 11, 'name': 'defi', 'alias': 'NexTrade', 'time_interval': 50, 'is_active': False, 'border_color': '#FF39C2', 'icon': '/static/topmenu_icons_resize/nextrade.png', 'created_at': '2024-03-08 14:34:14.445709'},
                {'id': 12, 'name': 'defio', 'alias': 'DiverseFi', 'time_interval': 50, 'is_active': False, 'border_color': '#C438B3', 'icon': '/static/topmenu_icons_resize/diverse_fi.png', 'created_at': '2024-03-08 14:34:14.675016'},
                {'id': 13, 'name': 'ai', 'alias': 'IntelliChain', 'time_interval': 50, 'is_active': False, 'border_color': '#895DF6', 'icon': '/static/topmenu_icons_resize/intellichain.png', 'created_at': '2024-03-08 14:34:14.837494'},
                {'id': 14, 'name': 'oracle', 'alias': 'TruthNodes', 'time_interval': 50, 'is_active': True, 'border_color': '#389AEA', 'icon': '/static/topmenu_icons_resize/truthnodes.png', 'created_at': '2024-03-08 14:34:13.728966'}
            ]
            
            for category_data in categories_data:
                new_category = Category(**category_data)
                db.session.add(new_category)
            db.session.commit()
            print("Fixed data inserted into the 'Category' table.")
        else:
            print("The 'Category' table is already populated.")
    except Exception as e:
        print(f"Error initializing categories: {e}")
        db.session.rollback()


def initialize_fixed_data():
    try:
        # Check if data already exists
        if db.session.query(Bot).count() == 0:
            # No data found, proceed to insert fixed data
            bots_fixed = [
                {'id': 1,'name': 'btc', 'category_id': 1},
                {'id': 2,'name': 'eth', 'category_id': 2},
                {'id': 3,'name': 'hacks', 'category_id': 3},
                {'id': 4,'name': 'ldo', 'category_id': 4},
                {'id': 5,'name': 'rpl', 'category_id': 4},
                {'id': 6,'name': 'fxs', 'category_id': 4},
                {'id': 7,'name': 'atom', 'category_id': 5},
                {'id': 8,'name': 'dot', 'category_id': 5},
                {'id': 9,'name': 'qnt', 'category_id': 5},
                {'id': 10,'name': 'ada', 'category_id': 6},
                {'id': 11,'name': 'sol', 'category_id': 6},
                {'id': 12,'name': 'avax', 'category_id': 6},
                {'id': 13,'name': 'near', 'category_id': 7},
                {'id': 14,'name': 'ftm', 'category_id': 7},
                {'id': 15,'name': 'kas', 'category_id': 7},
                {'id': 16,'name': 'arb', 'category_id': 8},
                {'id': 17,'name': 'op', 'category_id': 8},
                {'id': 18,'name': 'polygon', 'category_id': 8},
                {'id': 19,'name': 'link', 'category_id': 9},
                {'id': 20,'name': 'api3', 'category_id': 9},
                {'id': 21,'name': 'band', 'category_id': 9},
                {'id': 22,'name': 'xlm', 'category_id': 10},
                {'id': 23,'name': 'algo', 'category_id': 10},
                {'id': 24,'name': 'xrp', 'category_id': 10},
                {'id': 25,'name': 'dydx', 'category_id': 11},
                {'id': 26,'name': 'velo', 'category_id': 11},
                {'id': 27,'name': 'gmx', 'category_id': 11},
                {'id': 28,'name': 'uni', 'category_id': 12},
                {'id': 29,'name': 'sushi', 'category_id': 12},
                {'id': 30,'name': 'cake', 'category_id': 12},
                {'id': 31,'name': 'aave', 'category_id': 13},
                {'id': 32,'name': 'pendle', 'category_id': 13},
                {'id': 33,'name': '1inch', 'category_id': 13},
                {'id': 34,'name': 'ocean', 'category_id': 14},
                {'id': 35,'name': 'fet', 'category_id': 14},
                {'id': 36,'name': 'rndr', 'category_id': 14},
                {'id': 37,'name': 'total3', 'category_id': 1},
                {'id': 38,'name': 'sp500', 'category_id': 1},
                {'id': 39,'name': 'dxy', 'category_id': 1},
            ]

            for bot_data in bots_fixed:
                new_bot = Bot(**bot_data)
                db.session.add(new_bot)
            db.session.commit()
            print("Fixed data inserted into the 'Bot' table.")
        else:
            print("The 'Bot' table is already populated.")
    except Exception as e:
        print(f"Error initializing fixed data: {e}")
        db.session.rollback()



def initialize_sites_data():
    try:
        # Check if data already exists
        if db.session.query(Site).count() == 0:
            # No data found, proceed to insert fixed data
            sites_fixed = [
                {'name': 'Google News', 'url': '', 'bot_id': 1,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=ethereum%20%22ethereum%22%20when%3A1d%20-msn%20-buy&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 2,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=Crypto%20Hacks%20when%3A1d%20-Sead%20-medical%20-msn&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 3,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=LDO%20Lido%20%22LDO%22%20%22lido%22%20when%3A1d%20-msn&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 4,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=RPL%20crypto%20when%3A1d%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 5,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=Frax%20FXS%20when%3A1d%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 6,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=Cosmos%20ATOM%20%22Cosmos%22%20%22ATOM%22%20when%3A1d%20-INJ%20-msn&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 7,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=Polkadot%20DOT%20%22dot%22%20%22DOT%22%20%22Polkadot%22%20when%3A1d%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 8,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=Quant%20QNT%20%22Quant%22%20%20%22QNT%22%20when%3A1d%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 9,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=Cardano%20ADA%20%22Cardano%22%20when%3A1d%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 10,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=Solana%20SOL%20%22Sol%22%20%22Solana%22%20when%3A1d%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 11,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=Avalanche%20AVAX%20%22Avalanche%22%20%22AVAX%22%20when%3A1d%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 12,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=NEAR%20protocol%20%22Near%22%20%22NEAR%22%20when%3A1d%20-msn%20-top&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 13,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=FTM%20Fantom%20%22FTM%22%20%22Fantom%22%20when%3A1d%20-msn%20-medium%20-buy&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 14,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=KAS%20Kaspa%20%22KAS%22%20%22Kaspa%22%20when%3A1d%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 15,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=MATIC%20Polygon%20%22Polygon%22%20%22MATIC%22%20when%3A1d%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 16,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=ARB%20Arbitrum%20%22ARB%22%20%22Arbitrum%22%20when%3A1d%20-CEX%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 17,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=OP%20Optimism%20%22OP%22%20%22Optimism%22%20when%3A1d%20-AVAX%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 18,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=LINK%20Chainlink%20%22LINK%22%20%22Chainlink%22%20when%3A1d%20-medium%20-msn&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 19,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=API3%20Crypto%20when%3A1d&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 20,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=BAND%20Protocol%20%22BAND%20Protocol%22%20%22BAND%22%20when%3A1d%20-INJ%20-msn&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 21,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=XLM%20Stellar%20%22XLM%22%20%22Stellar%22%20when%3A1d%20-OTC%20-ADA%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 22,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=ALGO%20Algorand%20%22Algorand%20ALGO%22%20when%3A1d%20-DOGE%20-Dogecoin%20-msn&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 23,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=XRP%20Ripple%20%22Ripple%20XRP%22%20when%3A1d%20-msn%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 24,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=DYDX%20%22dydx%22%20crypto%20when%3A1d%20-msn&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 25,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=VELO%20Velodrome%20crypto%20%22VELO%22%20%22Velodrome%22%20when%3A1d%20-msn&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 26,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=GMX%20Crypto%20%22GMX%22%20when%3A1d%20-CEX%20-msn&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 27,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=UNI%20Uniswap%20%22UNI%22%20%22Uniswap%22%20when%3A1d%20-sushi%20-near%20-PICKS%20-MSN%20-msn&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 28,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=SUSHI%20Sushiswap%20%22SUSHI%22%20%22Sushiswap%20%22%20when%3A1d%20-medium%20-MSN&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 29,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=CAKE%20Pancakeswap%20%22CAKE%22%20%22Pancakeswap%22%20when%3A1d%20-MSN%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 30,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=AAVE%20Crypto%20%22AAVE%22%20when%3A1d%20-NEAR%20-UNI%20-UNISWAP%20-SHIBA%20-MSN%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 31,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=PENDLE%20crypto%20%22PENDLE%22%20when%3A1d%20-MSN%20-medium%20-blockDag&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 32,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=1INCH%20Crypto%20%221INCH%22%20when%3A1d%20-MSN%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 33,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=ocean%20protocol%20%22Ocean%20protocol%22%20when%3A1d%20-FET%20-RNDR%20-MSN%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 34,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=fetch%20ai%20%22Fetch%20Ai%22%20%22FET%22%20when%3A1d%20-MSN%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 35,},
                {'name': 'Google News', 'url': 'https://news.google.com/search?q=Render%20RNDR%20%22Render%22%20%22RNDR%22%20when%3A1d%20-MSN%20-medium&hl=en-US&gl=US&ceid=US%3Aen', 'bot_id': 36,},
            ]

            for site_data in sites_fixed:
                new_site = Site(**site_data)
                db.session.add(new_site)
            db.session.commit()
            print("Fixed data inserted into the 'Site' table.")
        else:
            print("The 'Site' table is already populated.")
    except Exception as e:
        print(f"Error initializing fixed data: {e}")
        db.session.rollback()

