

import logging
import os
import dotenv
dotenv.load_dotenv()

import requests
from slack_bolt import App, BoltContext
from slack_sdk.web import WebClient
from slack_sdk.http_retry.builtin_handlers import RateLimitErrorRetryHandler
import re
from app.bolt_listeners import before_authorize, register_listeners
from app.env import (
    USE_SLACK_LANGUAGE,
    SLACK_APP_LOG_LEVEL,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_API_TYPE,
    OPENAI_API_BASE,
    OPENAI_API_VERSION,
    OPENAI_DEPLOYMENT_ID,
)
from app.slack_ops import (
    build_home_tab,
    DEFAULT_HOME_TAB_MESSAGE,
    DEFAULT_HOME_TAB_CONFIGURE_LABEL,
)
from app.i18n import translate
from slack_bolt.adapter.socket_mode import SocketModeHandler

if __name__ == "__main__":
    uni_dict = {}
    

    logging.basicConfig(level=SLACK_APP_LOG_LEVEL)

    app = App(
        token=os.environ["SLACK_BOT_TOKEN"],
        before_authorize=before_authorize,
        process_before_response=True,
    )
    app.client.retry_handlers.append(RateLimitErrorRetryHandler(max_retry_count=2))

    register_listeners(app)

    @app.view("modal-identifier") # receives messagegs from the client input and parses it. 
    def handle_modal_submission(ack, body, client):
        # conv_list = client.conversations_list()
        # channel_id = response["channels"][0]["id"]

        ack()
        print("body --- ",body)
        values = body["view"]["state"]["values"]
        print("values: --- ",values)
        # option = values["view"]["state"]["values"]
        # selected_option = values["option_select"]["selected_option"]["value"]
        # entered_text = values["text_input"]["entered_text"]["value"]

        # Perform any desired actions with the submitted data
        # For example, send a message to a channel

        '''
        -- insert requests API call to our service with column names. 
        '''
        # requests.get()

        try:
            response = client.chat_postMessage(
                channel="channel_id", text=f"Selected option: {values}, Entered text: {values}"
            )
            print(response)
        except Exception as e:
            print(f"Failed to post message: {e.response['error']}")


    @app.command("/add_post_gres")  # this is the main function that defines user interaction flow
    def handle_command(ack, body, client):
        ack()

        try:
            client.views_open(
                trigger_id=body["trigger_id"],
                view={
                    "type": "modal",
                    "callback_id": "modal-identifier",
                    "title": {"type": "plain_text", "text": "Modal Title"},
                    "blocks": [
                        {
                            "type": "input",
                            "block_id": "option_select",
                            "label": {"type": "plain_text", "text": "Select the table you want to query"},
                            "element": {
                                "type": "static_select",
                                "action_id": "selected_option",
                                "options": [
                                    {"text": {"type": "plain_text", "text": "Table 1"}, "value": "option1"},
                                    {"text": {"type": "plain_text", "text": "Table 2"}, "value": "option2"},
                                    {"text": {"type": "plain_text", "text": "Table 3"}, "value": "option3"},
                                ],
                            },
                        },
                        {
                            "type": "input",
                            "block_id": "text_input",
                            "element": {"type": "plain_text_input", "action_id": "entered_text"},
                            "label": {"type": "plain_text", "text": "Enter the postgres url to connect the database."},
                        },
                    ],
                    "submit": {"type": "plain_text", "text": "Submit"},
                },
            )
        except Exception as e:
            print(f"Failed to open modal: {e.response['error']}")



    @app.event("app_home_opened")
    def render_home_tab(client: WebClient, context: BoltContext):
        print(context)
        already_set_api_key = os.environ["OPENAI_API_KEY"]
        if context.user_id not in uni_dict:
            uni_dict[context.user_id] = "true"
        

        text = translate(
            openai_api_key=already_set_api_key,
            context=context,
            text=DEFAULT_HOME_TAB_MESSAGE,
        )
        print(text)
        configure_label = translate(
            openai_api_key=already_set_api_key,
            context=context,
            text=DEFAULT_HOME_TAB_CONFIGURE_LABEL,
        )
        
        client.views_publish(
            user_id=context.user_id,
            view=build_home_tab(text, configure_label),
        )

    if USE_SLACK_LANGUAGE is True:

        @app.middleware
        def set_locale(
            context: BoltContext,
            client: WebClient,
            next_,
        ):
            user_id = context.actor_user_id or context.user_id
            user_info = client.users_info(user=user_id, include_locale=True)
            context["locale"] = user_info.get("user", {}).get("locale")
            next_()

    @app.middleware
    def set_openai_api_key(context: BoltContext, next_):
        context["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
        context["OPENAI_MODEL"] = OPENAI_MODEL
        context["OPENAI_TEMPERATURE"] = OPENAI_TEMPERATURE
        context["OPENAI_API_TYPE"] = OPENAI_API_TYPE
        context["OPENAI_API_BASE"] = OPENAI_API_BASE
        context["OPENAI_API_VERSION"] = OPENAI_API_VERSION
        context["OPENAI_DEPLOYMENT_ID"] = OPENAI_DEPLOYMENT_ID
        next_()

    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
