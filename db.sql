-- Crear la tabla 'bot'
CREATE TABLE bot (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    sites_id INTEGER,
    keywords_id INTEGER,
    blacklist_id INTEGER,
    articles_id INTEGER,
    category_id INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (sites_id) REFERENCES site(id),
    FOREIGN KEY (keywords_id) REFERENCES keyword(id),
    FOREIGN KEY (blacklist_id) REFERENCES blacklist(id),
    FOREIGN KEY (articles_id) REFERENCES article(id),
    FOREIGN KEY (category_id) REFERENCES category(id)
);
-- Crear la tabla 'category'
CREATE TABLE category (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    alias VARCHAR,
    is_active BOOLEAN,
    border_color VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);


-- Crear la tabla 'site'
CREATE TABLE site (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    url VARCHAR,
    bot_id INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bot(id)
);

-- Crear la tabla 'keyword'
CREATE TABLE keyword (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    bot_id INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bot(id)
);

-- Crear la tabla 'blacklist'
CREATE TABLE blacklist (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    bot_id INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bot(id)
);

-- Crear la tabla 'article'
CREATE TABLE article (
    id SERIAL PRIMARY KEY,
    title VARCHAR,
    content TEXT,
    analysis TEXT,
    url VARCHAR,
    date TIMESTAMP,
    used_keywords VARCHAR,
    is_article_efficent VARCHAR,
    bot_id INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bot(id)
);

-- Crear la tabla 'unwanted_article'
CREATE TABLE unwanted_article (
    id SERIAL PRIMARY KEY,
    title VARCHAR,
    content TEXT,
    analysis TEXT,
    url VARCHAR,
    date TIMESTAMP,
    used_keywords VARCHAR,
    is_article_efficent VARCHAR,
    bot_id INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bot(id)
);
