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
        self.
        
    def now_time(self):
        return datetime.now().astimezone().isoformat()
    def stream_log_search(self,word,vector_search=False):

    def get_stream_topic(self,word=None):

    def get_user_topic(self,word=None):
        
    def user_log_search(self,word,vector_search=False):
        pass
    def tools(self):
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
        TOOLS=[
            #now_time関数
            {
            "type": "function",
                "function": {
                    "name": "now_time",
                    "description": "Get the current time, including the time zone",
                    "parameters": {},
            },
            },
            #stream_log_search関数
            {
            "type": "function",
                "function": {
                    "name": "stream_search",
                    "description": "Search for specific content within the comments on a stream",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "word": {
                                "type": "string",
                                "description": "Search term",
                            },
                            "vertor_search": {
                                "type": "bool",
                                "description": "Set to true when searching based on semantic vectors",
                            },
                    },
                    "required": ["word"],
                },
            },
            },  
            #get_stream_topic関数
            {
            "type": "function",
                "function": {
                    "name": "get_stream_topic",
                    "description": "Search for topics discussed during the stream",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "word": {
                                "type": "string",
                                "description": "Search term",
                            },
                    },
                },
            },
            },
            #get_user_topic関数
            {
            "type": "function",
                "function": {
                    "name": "get_user_topic",
                    "description": "Search for topics discussed during conversations with users",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "word": {
                                "type": "string",
                                "description": "Search term",
                            },
                    },
                },
            },
            },
            #user_log_search関数
            {
            "type": "function",
                "function": {
                    "name": "user_log_search",
                    "description": "Search for specific content within comments found in user logs.",
                     "parameters": {
                        "type": "object",
                        "properties": {
                            "word": {
                                "type": "string",
                                "description": "Search term",
                            },
                            "vertor_search": {
                                "type": "bool",
                                "description": "Set to true when searching based on semantic vectors",
                            },
                    },
                    "required": ["word"],
                },
            },
            }

        ]
        AVAILABLE_FUNCTIONS = {
            "now_time": self.now_time,
            "stream_log_search": self.stream_log_search,
            "get_stream_topic":self.get_stream_topic,
            "get_user_topic":self.get_user_topic,
            "user_log_search":self.user_log_search
                }
        return TOOLS,AVAILABLE_FUNCTIONS
if __name__=="__main__":
    tool=Tools()
    print(tool.now_time())
