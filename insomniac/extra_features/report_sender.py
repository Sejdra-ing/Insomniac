import asyncio
import inspect
import json
import pathlib

from insomniac.utils import *


def notify_interaction_targets_finished(username):
    if not notification_chat_bot.init():
        return

    folder_name = pathlib.Path(__file__).parts[-4]
    notification_chat_bot.send_message(f"Interaction targets for `{username}` are finished! `{folder_name}`.")


def notify_unfollow_targets_finished(username):
    if not notification_chat_bot.init():
        return

    folder_name = pathlib.Path(__file__).parts[-4]
    notification_chat_bot.send_message(f"Unfollow targets for `{username}` are finished! `{folder_name}`.")


class NotificationChatBot:
    CONFIG_FILENAME = "telegram_notification_chat_bot_config.json"
    CONFIG_KEY_TOKEN = "token"
    CONFIG_KEY_CHAT_ID = "chat_id"

    is_initialized = False
    is_initialization_failed = False
    token = ""
    chat_id = ""
    bot = None

    def init(self) -> bool:
        if self.is_initialized:
            return True

        if self.is_initialization_failed:
            return False

        try:
            from telegram import Bot

            with open(self.CONFIG_FILENAME, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                self.token = data[self.CONFIG_KEY_TOKEN]
                self.chat_id = data[self.CONFIG_KEY_CHAT_ID]

            self.bot = Bot(self.token)
        except Exception as e:
            print_debug(COLOR_FAIL + f"Failed initialization of NotificationChatBot: {e}" + COLOR_ENDC)
            self.is_initialization_failed = True
            return False

        self.is_initialized = True
        return True

    def send_message(self, text):
        print_debug(f"Sending message in NotificationChatBot: \"{text}\"")
        try:
            from telegram.constants import ParseMode  # python-telegram-bot >= 20
        except ImportError:
            from telegram import ParseMode
        try:
            result = self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode=ParseMode.MARKDOWN)
            # python-telegram-bot >= 20 is async
            if inspect.isawaitable(result):
                asyncio.run(result)
        except Exception as e:
            print_debug(COLOR_FAIL + f"Failed to send message in NotificationChatBot: {e}" + COLOR_ENDC)


notification_chat_bot = NotificationChatBot()
