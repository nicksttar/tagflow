from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    video_topic = State()
    video_style = State()
    post_topic = State()
    post_style = State()
    tag_topic = State()
    generated_pull_name = State()
    pull_name = State()
    pull_tags = State()
    pull_edit_name = State()
