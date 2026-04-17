from data.database import Database


db = Database()


async def create_db():
    await db.create_db()


async def create_user_data(user_id, topic, style, content):
    await db.save_post(user_id=user_id, topic=topic, style=style, content=content)


async def add_tag_pool(user_id, name, tags):
    await db.add_tag_pool(user_id=user_id, tags_name=name, tags_content=tags)


async def get_tag_pools(user_id):
    return await db.show_user_data(user_id)


async def delete_tag_pool(pool_id, user_id):
    return await db.delete_pack_by_id(pool_id, user_id)


async def edit_tag_pool(pool_id, user_id, tags):
    return await db.replace_pack(pool_id, user_id, tags)
