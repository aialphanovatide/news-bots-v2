-- Crear la tabla 'bot'
CREATE TABLE bot (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    dalle_prompt VARCHAR,
    category_id INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
-- Crear la tabla 'category'

CREATE TABLE category (
    id SERIAL PRIMARY KEY,
    name VARCHAR,
    alias VARCHAR,
    prompt VARCHAR,
    time_interval INTEGER,
    icon VARCHAR,
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
    is_top_soty BOOLEAN,
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


-- Create UsedKeywords table
CREATE TABLE used_keywords (
    id SERIAL PRIMARY KEY,
    article_content VARCHAR,
    article_date VARCHAR,
    article_url VARCHAR,
    keywords VARCHAR,
    source VARCHAR,
    article_id INTEGER,
    bot_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES article(id),
    FOREIGN KEY (bot_id) REFERENCES bot(id)
);