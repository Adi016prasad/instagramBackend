import json
from flask import Flask
from flask import request
import logging
from google import genai
from google.genai import types
import requests
from PIL import Image
import os

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@app.route("/")
def hello_world():
    return "Hello world"

@app.route("/privacy_policy")
def privacy_policy():
    with open ("./privacy_policy.html","rb") as file:
        privacy_policy_html = file.read()
    return privacy_policy_html

@app.route("/webhook", methods = ["GET","POST"])
def webhook():
    if request.method == "POST":
        try:
            data = request.get_json()
            logger.info("Received the data : %s", data)
            # if data["entry"][0]["messaging"][0]["sender"]["id"] == "17841477375558280":
            #     logger.info("Ignoring message from self")
            #     return "Ignored self message", 200
            entry = data.get("entry", [])[0]

            if "messaging" in entry and "read" in entry["messaging"][0]:
                logger.info("Person has read the message")
                return "person has read", 200
            else:
                if "changes" in entry:
                    if data["entry"][0]["changes"][0]["value"]["from"]["id"] == "17841477375558280":
                        logger.info("Comments is posted")
                        return "comments is posted", 200
                    else:
                        if data["entry"][0]["changes"][0]["field"] == "comments":
                            logger.info("Received the comments on media")
                            handleCommentsOnMedia(data)
                        else:
                            logger.info("Received something wrong webhook")
                
                elif "messaging" in entry:
                    if data["entry"][0]["messaging"][0]["sender"]["id"] == "17841477375558280":
                        logger.info("Ignoring message from self")
                        return "Ignored self message", 200

                    messaging_event = data["entry"][0]["messaging"][0]

                    if "message" in messaging_event:   # ✅ only when "message" exists
                        message = messaging_event["message"]

                        if "text" in message:
                            msg_type = "text"
                            content = message["text"]
                            res = handleMessagesOnDirectMessages(data)
                            logger.info("Message sent to user %s", res)

                        elif "attachments" in message:
                            msg_type = message["attachments"][0]["type"]
                            content = message["attachments"][0]["payload"]["url"]
                            res = handleImageOnDirectMessages(data)
                            logger.info("Message sent to user for image %s", res)

                    elif "read" in messaging_event:
                        logger.info("Person has read the message")
                        return "person has read", 200

                else:
                    logger.info("Received a messaging event without 'message' or 'read'")

        except Exception as e:
            logger.exception("Error handling webhook: %s", e)
            return "Internal Server Error", 500

        return "POST received", 200

    
    if request.method == "GET":
        hub_mode = request.args.get("hub.mode")
        hub_challenge = request.args.get("hub.challenge")
        hub_verify_token = request.args.get("hub.verify_token")
        if hub_challenge:
            return hub_challenge
        else:
            return "This is GET request, hello webhook"

# def captureMedias():
#     logger.info("inside the medias")
#     url = "https://graph.facebook.com/v23.0/17841477375558280/media"
#     params = {
#         "fields": "id,caption,permalink"
#     }
#     headers = {
#         "Authorization": "Bearer EAAL01TOxmTsBPoD96ZCWfZBbTechtrUHC0JOVXqwA1adbZCviRInVnG5yhVdlRsAOOftbDzqTQz1dcsX3ZAMjV6bVg0ZB7CebMT9itx5pvPIvfqdxdYmcCGJHq5yUZAvZBSl250s5cMFMXs5YxZCibAeeSpFtX3C4REYMCzVrmqMnjMrW7V3plUeqPJyfDUOyv09"
#     }
#     logger.info("sent the request")
#     response = requests.get(url, headers=headers, params=params)
#     data = response.json()

#     arrayMedias = []
#     for media in data["data"]:
#         arrayMedias.append(media["id"])

#     logger.info("medias %s", arrayMedias)
#     return arrayMedias

def handleCommentsOnMedia(data):
    try:
        logger.info("Inside the handlecommentsOnMedia")
        responseFromLlm = handleLlmResponse(data["entry"][0]["changes"][0]["value"]["text"])
        comment_id = data["entry"][0]["changes"][0]["value"]["id"]
        logger.info ("comment id received is : %s", comment_id )
        reply_text = responseFromLlm
        url = f"https://graph.instagram.com/v23.0/{comment_id}/replies?message={reply_text}"

        logger.info("url %s", url)
        headers = {
            "Authorization": "Bearer IGAAYVvHGDxIxBZAFBQcDZAJQW1lMmJjQTREZAUozWUsxcXdMUE41UWIwZA29RRmxNVFNVeUlPXzVhOXRFN2t3VmpSNGtMYTZA6dGZABMEtmMXVlZATlYZAWZAXWTA4QUN0WEJUM0hUdUNBSDY3UnRURExIcnpWTnJMQkZAReHlqSEFFODVOawZDZD"
        }
        response = requests.post(url, headers=headers)
        logger.info("response:%s",response)
        logger.info("Response:", response.json())

    except requests.exceptions.RequestException as e:
        logger.exception("Requests error occurred: %s", e)

    except Exception as e:
        logger.exception("Unexpected error occurred: %s", e)


def handleMessagesOnDirectMessages(data):
    # value = data.get("value", {})
    # sender_id = value.get("sender", {}).get("id")
    # recipient_id = value.get("recipient", {}).get("id")
    # timestamp = value.get("timestamp")
    # message_mid = value.get("message", {}).get("mid")
    # text = value.get("message", {}).get("text")
    # logger.info("Webhook (messages): sender_id=%s recipient_id=%s timestamp=%s message_mid=%s message_text=%s", sender_id, recipient_id, timestamp, message_mid, text)
    sender_id, text = data["entry"][0]["messaging"][0]["sender"]["id"], data["entry"][0]["messaging"][0]["message"]["text"]
    responseFromLlm = handleLlmResponse(text)
    logger.info("llm %s", responseFromLlm)
    user_access_token = "IGAAYVvHGDxIxBZAFBQcDZAJQW1lMmJjQTREZAUozWUsxcXdMUE41UWIwZA29RRmxNVFNVeUlPXzVhOXRFN2t3VmpSNGtMYTZA6dGZABMEtmMXVlZATlYZAWZAXWTA4QUN0WEJUM0hUdUNBSDY3UnRURExIcnpWTnJMQkZAReHlqSEFFODVOawZDZD"
    url = f"https://graph.instagram.com/v23.0/me/messages"
    headers = {"Authorization": f"Bearer {user_access_token}","Content-Type":"application/json"}
    json_body = {
        "recipient":{
            "id": sender_id
        },
        "message":{
            "text":responseFromLlm
        }
    }

    response = requests.post(url, headers = headers, json = json_body)
    data = response.json()
    logger.info("data",data)
    return responseFromLlm

def handleImageOnDirectMessages(data):
    try:
        sender_id = data["entry"][0]["messaging"][0]["sender"]["id"]
        logger.info("sender id %s", sender_id)
        image_path = data["entry"][0]["messaging"][0]["message"]["attachments"][0]["payload"]["url"]
        logger.info("image path %s", image_path)
        image_bytes = requests.get(image_path).content
        #logger.info("image bytes %s", image_bytes)
        #mime_type = detectMimeType(image_bytes)
        #logger.info("mime type %s",mime_type)
        image = types.Part.from_bytes(
        data=image_bytes, mime_type="image/jpeg"
        )
        #logger.info("image %s",image)
        client = genai.Client(api_key = "AIzaSyAFuVoSah1AWTVv2H_oKnJhimANCGjCVg8")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=["Analyze the image carefully and give the answer", image],
        )

        user_access_token = "IGAAYVvHGDxIxBZAFBQcDZAJQW1lMmJjQTREZAUozWUsxcXdMUE41UWIwZA29RRmxNVFNVeUlPXzVhOXRFN2t3VmpSNGtMYTZA6dGZABMEtmMXVlZATlYZAWZAXWTA4QUN0WEJUM0hUdUNBSDY3UnRURExIcnpWTnJMQkZAReHlqSEFFODVOawZDZD"
        url = f"https://graph.instagram.com/v23.0/me/messages"
        headers = {"Authorization": f"Bearer {user_access_token}","Content-Type":"application/json"}
        trimmed_message = response.text[:250]
        json_body = {
            "recipient":{
                "id": sender_id
            },
            "message":{
                "text":trimmed_message
            }
        }

        response = requests.post(url, headers = headers, json = json_body)
        data = response.json()
        logger.info("Image has been processed")
        return response.text
        # client = genai.Client(api_key = "AIzaSyAFuVoSah1AWTVv2H_oKnJhimANCGjCVg8")
        # response = client.models.generate_content(
        #     model='gemini-2.0-flash-001',
        #     contents = text,
        #     config = types.GenerateContentConfig(
        #         system_instruction = "Analyze the image and tell something about it",
        #         max_output_tokens = 30,
        #         temperature = 0.8
        #     )
        # )
        # logger.info("LLM response generated : %s", response.text)
        # return response.text
    except requests.exceptions.RequestException as e:
        logger.exception("Requests error occurred: %s", e)

    except Exception as e:
        logger.exception("Unexpected error occurred: %s", e)

# def detectMimeType(path):
#     try:
#         with Image.open(path) as img:
#             img_type = img.format
#             return img_type
#     except IOError:
#         return None

def handleLlmResponse(text):
    try:
        logger.info("text %s", text)
        client = genai.Client(api_key = "AIzaSyAFuVoSah1AWTVv2H_oKnJhimANCGjCVg8")
        response = client.models.generate_content(
            model='gemini-2.0-flash-001',
            # model = 'gemini-2.5-flash',
            contents = text,
            config = types.GenerateContentConfig(
                system_instruction = "You are a sport person and you are very good in sports",
                max_output_tokens = 50,
                temperature = 0.8
            )
        )
        logger.info("LLM response generated : %s", response.text)
        return response.text
    except:
        logger.info("Issue is generation of response")



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
