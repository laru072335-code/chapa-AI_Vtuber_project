"""
AIが使うツールについてまとめたもの

{
"type": "function",
"function": {
    "name": "get_current_weather",
    "description": "Get the current weather in a given location",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA",
            },
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
        },
        "required": ["location"],
    },
},
}
これが基礎系
"""
from datetime import datetime
from type_list import *
class Tools:
    def __init__(self,setting:Settings):
        self.setting=setting

        
    def now_time(self):
        return datetime.now().astimezone().isoformat()
    def stream_search(self,word,vector_search=False):

    def get_stream_topic(self,word=None):

    def get_user_topic(self,word=None):
        
    def user_search(self,word,vector_search=False):

    def get_user_profile(self):


    def tools():
        """
        ### litellmにの引数のtoolsに渡すリストとAVAILABLE_FUNCTIONSを返す。
        tools=[{\n
            "type": "function",
                "function": {
                    "name": "get_current_weather",
                    "description": "Get the current weather in a given location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA",
                            },
                            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
            }]\n
        AVAILABLE_FUNCTIONS = {
        "get_current_weather": get_current_weather,
        "get_weather_advice": get_weather_advice,
            }
        """
        AVAILABLE_FUNCTIONS = {
            "get_current_weather": get_current_weather,
            "get_weather_advice": get_weather_advice,
                }
        pass

if __name__=="__main__":
    print(now_time())
