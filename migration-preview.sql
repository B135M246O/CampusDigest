BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 6547cda9ef8b

CREATE TABLE article (
    date TIMESTAMP WITH TIME ZONE NOT NULL, 
    category VARCHAR NOT NULL, 
    title VARCHAR NOT NULL, 
    overview TEXT, 
    text TEXT, 
    link VARCHAR NOT NULL, 
    picture_link VARCHAR, 
    source VARCHAR NOT NULL, 
    id SERIAL NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (link)
);

CREATE TABLE author (
    article_id INTEGER NOT NULL, 
    author_name VARCHAR NOT NULL, 
    id SERIAL NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(article_id) REFERENCES article (id)
);

CREATE TABLE infographic (
    article_id INTEGER NOT NULL, 
    infographic_link VARCHAR NOT NULL, 
    id SERIAL NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(article_id) REFERENCES article (id)
);

INSERT INTO alembic_version (version_num) VALUES ('6547cda9ef8b') RETURNING alembic_version.version_num;

-- Running upgrade 6547cda9ef8b -> 277a7f3ade68

UPDATE alembic_version SET version_num='277a7f3ade68' WHERE alembic_version.version_num = '6547cda9ef8b';

-- Running upgrade 277a7f3ade68 -> 44c042d1297b

ALTER TABLE article ADD COLUMN video_link VARCHAR;

UPDATE alembic_version SET version_num='44c042d1297b' WHERE alembic_version.version_num = '277a7f3ade68';

-- Running upgrade 44c042d1297b -> 7c60f284cfcf

ALTER TABLE author DROP CONSTRAINT author_article_id_fkey;

ALTER TABLE author ADD FOREIGN KEY(article_id) REFERENCES article (id) ON DELETE CASCADE;

ALTER TABLE infographic DROP CONSTRAINT infographic_article_id_fkey;

ALTER TABLE infographic ADD FOREIGN KEY(article_id) REFERENCES article (id) ON DELETE CASCADE;

UPDATE alembic_version SET version_num='7c60f284cfcf' WHERE alembic_version.version_num = '44c042d1297b';

-- Running upgrade 7c60f284cfcf -> 0112e416d455

CREATE TABLE "user" (
    chat_id INTEGER NOT NULL, 
    email VARCHAR(320) NOT NULL, 
    hashed_password VARCHAR(1024) NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    is_superuser BOOLEAN NOT NULL, 
    is_verified BOOLEAN NOT NULL, 
    id SERIAL NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_user_chat_id ON "user" (chat_id);

CREATE UNIQUE INDEX ix_user_email ON "user" (email);

UPDATE alembic_version SET version_num='0112e416d455' WHERE alembic_version.version_num = '7c60f284cfcf';

-- Running upgrade 0112e416d455 -> da0f329dac4d

CREATE TABLE articleuser (
    article_id INTEGER NOT NULL, 
    user_id INTEGER NOT NULL, 
    id SERIAL NOT NULL, 
    PRIMARY KEY (article_id, user_id, id), 
    FOREIGN KEY(article_id) REFERENCES article (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES "user" (id) ON DELETE CASCADE
);

UPDATE alembic_version SET version_num='da0f329dac4d' WHERE alembic_version.version_num = '0112e416d455';

-- Running upgrade da0f329dac4d -> 42ec8808acf7

UPDATE alembic_version SET version_num='42ec8808acf7' WHERE alembic_version.version_num = 'da0f329dac4d';

-- Running upgrade 42ec8808acf7 -> 04d5a25a9a5f

ALTER TABLE "user" ADD COLUMN article_limit INTEGER NOT NULL;

UPDATE alembic_version SET version_num='04d5a25a9a5f' WHERE alembic_version.version_num = '42ec8808acf7';

-- Running upgrade 04d5a25a9a5f -> 4eab5418ff11

ALTER TABLE "user" ALTER COLUMN chat_id DROP NOT NULL;

UPDATE alembic_version SET version_num='4eab5418ff11' WHERE alembic_version.version_num = '04d5a25a9a5f';

-- Running upgrade 4eab5418ff11 -> 4eacd65ddb52

ALTER TABLE article ADD COLUMN video_preview_link VARCHAR;

UPDATE alembic_version SET version_num='4eacd65ddb52' WHERE alembic_version.version_num = '4eab5418ff11';

-- Running upgrade 4eacd65ddb52 -> c41d6a2b0e19

DELETE FROM articleuser WHERE id NOT IN (SELECT MIN(id) FROM articleuser GROUP BY article_id, user_id);

ALTER TABLE articleuser DROP CONSTRAINT articleuser_pkey;

ALTER TABLE articleuser ADD CONSTRAINT articleuser_pkey PRIMARY KEY (id);

ALTER TABLE articleuser ADD CONSTRAINT uq_articleuser_article_user UNIQUE (article_id, user_id);

UPDATE alembic_version SET version_num='c41d6a2b0e19' WHERE alembic_version.version_num = '4eacd65ddb52';

COMMIT;

