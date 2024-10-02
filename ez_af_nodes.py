import re
import os
from server import PromptServer # type: ignore # - server is a part of ComfyUI Core
from aiohttp import web

#REQUIRES Pythongosssss extensions to work. #Thank you pythongosssss!

prompts_path = os.path.abspath(os.path.join(__file__, "../CSV")) #Global var: path to CSV folder
#Under normal conditions this would be equal to ...\ComfyUI\custom_nodes\ComfyUI-EZ-AF-Nodes\CSV

@PromptServer.instance.routes.get("/pysssss/prompt-line/{name}") #Actually the most important pre-execution part. This is why this node can show second input based on the first one and update in 
async def get_prompts(request):
    name = request.match_info["name"]
    name = name.replace("⧵","/")
    csv_path = os.path.abspath(os.path.join(__file__, "../CSV/",name))
    prompts = {"Error loading .csv file (Front), check the console": ["",""]}
    if not os.path.exists(csv_path):
        print(f"""Error. No .csv file found. """)
        return prompts
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = [line for line in f.readlines()[1:] if line.strip()]
            prompts = [
                [x.replace('"', '').replace('\n', '') for x in re.split(';(?=(?:[^"]*"[^"]*")*[^"]*$)', line)]
                for line in lines
            ]
            prompts = {x[0]: [x[1], x[2]] for x in prompts}
    except Exception as e:
        print(f"""Error loading .csv file (Front). Error: {e} """)

    prompts_list = list(prompts.keys())

    if len(prompts_list) == 0:
        prompts_list = ["[none]"]
    return web.json_response(prompts_list)

def clean_text(text):
    
    text = re.sub(r'\n','####', text) # Replace line breaks to keep it for future (line breaks should not be deleted by default
    text = re.sub(r'\s+,', ',', text) # Remove spaces before commas
    text = re.sub(r',+', ',', text) # Remove duplicate commas
    text = re.sub(r',(\S)', r', \1', text) # Add a space after a comma if it's followed by a word without space
    text = re.sub(r'[ \t]+', ' ', text) # Replace multiple spaces with a single space, while keeping newlines
    text = re.sub(r'\.,|,\.', '.', text) # Replace incorrect combinations like '.,' and ',.' with '.'
    text = re.sub(r"####",'\n', text) # Return line breaks
    text = re.sub(r'(\n\s*){3,}', '\n\n', text) # Consolidate three or more consecutive newlines into two
    text = text.strip().replace(" .", ".") # Remove spaces before periods
    text = re.sub(r',(\S)', r' ', text) # Add a space after a comma if it's followed by a word without space
    cleaned_lines = [line.lstrip("., ") for line in text.splitlines()] # Delete excess commas
    text = "\n".join(cleaned_lines)

    return text

def get_prompt(csv_file, prompt): #I know this is repeated, not optimized, Sorry. Code stolen from CSV Loader by PCMonsterx (I modified divider "," > ";" so that it's easier to write prompts and edit in excel)
    global prompts_path
    if prompt == "[none]" or not prompt or not prompt.strip():
        raise ValueError("No prompt")

    csv_file = csv_file.replace("⧵","/")
    csv_path = os.path.join(prompts_path, csv_file)

    prompts = {"Error loading .csv file (Back), check the console": ["",""]}
    if not os.path.exists(csv_path):
        print(f"""Error. No .csv file found.""")
        return prompts
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = [line for line in f.readlines()[1:] if line.strip()]
            prompts = [
                [x.replace('"', '').replace('\n', '') for x in re.split(';(?=(?:[^"]*"[^"]*")*[^"]*$)', line)]
                for line in lines
            ]
            prompts = {x[0]: [x[1], x[2]] for x in prompts}
    except Exception as e:
        print(f"""Error loading .csv file (Back). Error: {e} """)

    prompts_list = list(prompts.keys())
    if len(prompts_list) == 0:
        prompts = ["[none]"]
    
    return (prompts[prompt][0],prompts[prompt][1])


class TextFileNode:
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive prompt", "negative prompt")
    CATEGORY = "EZ-AF-Nodes"

    @classmethod
    def VALIDATE_INPUTS(self, csv_file, prompt, **kwargs):
        if prompt == "[none]" or not prompt or not prompt.strip(): 
            return True #Always validate if nothing is selected
        get_prompt(csv_file, prompt) #redo the code for validation
        return True 

    def load_text(self, **kwargs): #execution is here
        self.prompt = get_prompt(kwargs["csv_file"], kwargs["prompt"])
        return self.prompt

class EZCSVRead(TextFileNode):
    @classmethod
    def IS_CHANGED(self, **kwargs):
        #return os.path.getmtime(self.file) i don't undertand why this one was necessary
        return float("nan")

    @classmethod
    def INPUT_TYPES(s):
        global prompts_path #Code stolen from Inspire-Pack by ltdrdata 
        try:
            prompt_files = []
            for root, dirs, files in os.walk(prompts_path): #collects all files in the directory. No subdirectories support currently (but it's possible)
                for file in files:
                    if file.endswith(".csv"):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, prompts_path)
                        rel_path = rel_path.replace("\\","⧵") #replacement needed as normal slash changes url, disabling server update for second input
                        prompt_files.append(rel_path)
        except Exception:
            prompt_files = []

        return {
            "required": {
                "csv_file": (prompt_files,), # ! here we determine variable
                "prompt": (["[none]"], { #important part that uses pysssss extension
                    "pysssss.binding": [{ #it passes the first variable to server to determine input list for the second one without triggering queue or refreshing page. Genius
                        "source": "csv_file", # ! here we pass that variable
                        "callback": [{
                            "type": "set",
                            "target": "$this.disabled", #disables second input by default
                            "value": True
                        }, {
                            "type": "fetch",
                            "url": "/pysssss/prompt-line/{$source.value}", #this address passes the "sorce" value
                            "then": [{
                                "type": "set",
                                "target": "$this.options.values",
                                "value": "$result"
                            }, {
                                "type": "validate-combo"
                            }, {
                                "type": "set",
                                "target": "$this.disabled", #enables second input if valid
                                "value": False
                            }]
                        }],
                    }]
                })
            },
        }

    FUNCTION = "load_text"

# MEGA-CONCATENATE-TEXT #

class EZConcatText: #Code stolen from WAS-Suite by Jordan Thompson (WASasquatch), i only added more optional inputs :) Comments by original author kept as they were.

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "delimiter": ("STRING", {"default": "\\n"}),
                "beautify": (["never", "before", "after"], {"default": "never"}),
                "line_breaks": (["keep", "delete"], {"default": "keep"}),
            },
            "optional": {
                "text_01": ("STRING", {"forceInput": True}),
                "text_02": ("STRING", {"forceInput": True}),
                "text_03": ("STRING", {"forceInput": True}),
                "text_04": ("STRING", {"forceInput": True}),
                "text_05": ("STRING", {"forceInput": True}),
                "text_06": ("STRING", {"forceInput": True}),
                "text_07": ("STRING", {"forceInput": True}),
                "text_08": ("STRING", {"forceInput": True}),
                "text_09": ("STRING", {"forceInput": True}),
                "text_10": ("STRING", {"forceInput": True}),
                "text_11": ("STRING", {"forceInput": True}),
                "text_12": ("STRING", {"forceInput": True}),
                "text_13": ("STRING", {"forceInput": True}),
                "text_14": ("STRING", {"forceInput": True}),
                "text_15": ("STRING", {"forceInput": True}),
                "text_16": ("STRING", {"forceInput": True}),
                "text_17": ("STRING", {"forceInput": True}),
                "text_18": ("STRING", {"forceInput": True}),
                "text_19": ("STRING", {"forceInput": True}),
                "text_20": ("STRING", {"forceInput": True}),
                "text_21": ("STRING", {"forceInput": True}),
                "text_22": ("STRING", {"forceInput": True}),
                "text_23": ("STRING", {"forceInput": True}),
                "text_24": ("STRING", {"forceInput": True}),
            }
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "text_concatenate"

    CATEGORY = "EZ-AF-Nodes"

    def text_concatenate(self, delimiter, beautify, line_breaks, **kwargs):
        text_inputs = []

        # Handle special case where delimiter is "\n" (literal newline). 
        delimiter=delimiter.replace("\\n","\n")

        # Iterate over the received inputs in sorted order.
        for k in sorted(kwargs.keys()):
            v = kwargs[k]

            # Only process string input ports.
            if isinstance(v, str):
                if beautify == "before":
                        v=clean_text(v)
                if v != "":
                    text_inputs.append(v)

        # Merge the inputs. Will always generate an output, even if empty.
        merged_text = delimiter.join(text_inputs)
        print(merged_text)
        if beautify == "after":
            merged_text = clean_text(merged_text)
        if line_breaks == "delete":
            merged_text = re.sub(r'\n',' ', merged_text)
            merged_text = re.sub(r'\s+', ' ', merged_text)
        return (merged_text,)

# STRING (STRING+COMBO OUTPUT) #

class AnyType(str):
    def __ne__(self, __value: object) -> bool:
        return False

any = AnyType("*")

class EZString:

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "String": ("STRING", {"multiline": True}),
            }
        }

    RETURN_TYPES = (any, )
    RETURN_NAMES = ("any", )
    FUNCTION = "to_string"
    CATEGORY = "EZ-AF-Nodes"

    def to_string(self, String):
        
        Combo = String
        return (Combo, )


NODE_CLASS_MAPPINGS = {
    "EZ Load from CSV": EZCSVRead,
    "EZ Concatenate Text": EZConcatText,
    "EZ String": EZString,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "EZ Load from CSV": "EZ CSV Reader",
    "EZ Concatenate Text": "EZ MEGA Concat (Text)",
    "EZ String": "EZ String",
}
