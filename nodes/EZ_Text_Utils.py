import re

class EZ_Extract_Prompt:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string": ("STRING", {"multiline": True, "default": "", "forceInput": True, "tooltip": "Text to be processed."}),
                "searchword": ("STRING", {"multiline": False, "default": "", "tooltip": "Header name to be searched."}),
                "extract_all": ("BOOLEAN", {"default": False, "tooltip": "If true, extracts the original text of all headers, removing extra line breaks."}),
                "pass_original": ("BOOLEAN", {"default": False, "tooltip": "If true, passes the original input to output when no searchword is found."}),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "extract_prompt"
    OUTPUT_TOOLTIPS = ("Processed text.",)

    CATEGORY = "EZ NODES"

    DESCRIPTION = "Extracts lines of text based on the searchword"

    def extract_prompt(self, string, searchword, extract_all, pass_original):
        if extract_all:
            result = []
            for line in string.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue  # Skip empty lines
                if stripped.endswith(":") and len(stripped.split()) == 1:
                    continue  # Skip headers
                result.append(line)
            return ("\n".join(result),)

        searchword = searchword.lower()
        
        # Split input by separator to handle multiple entries
        entries = string.split('---')
        all_matches = []
        
        for entry in entries:
            collect = False
            lines_out = []
            
            for line in entry.splitlines():
                if not collect:
                    # Detect header line
                    header = line.strip()
                    if header.lower().rstrip(':') == searchword:
                        collect = True
                    continue

                # Stop collecting when we hit another header or empty line followed by header
                stripped_line = line.strip()
                if stripped_line == "":
                    continue  # Skip empty lines but don't stop collecting
                
                # Check if this is a new header (ends with : and is a single word)
                if stripped_line.endswith(":") and len(stripped_line.split()) == 1:
                    break  # Stop collecting when we hit a new header
                    
                lines_out.append(line)
            
            if lines_out:
                all_matches.extend(lines_out)

        result = "\n".join(all_matches)
        
        # If no content was extracted and pass_original is True, return the original string
        if not result.strip() and pass_original:
            return (string,)
        
        return (result,)
        
class EZ_Find_Replace:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string": ("STRING", {"multiline": True, "default": "", "forceInput": True}),
            },
            "optional": {
                "find": ("STRING", {"multiline": False, "default": ""}),
                "replace": ("STRING", {"multiline": False, "default": ""}),
            },
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "find_replace"
    CATEGORY = "EZ NODES"
    DESCRIPTION = "Finds and replaces all instances of text string."

    def find_replace(self, string, find, replace):
        string = string.replace(find, replace)
        return (string,)

class EZ_Text_to_Size:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_input": ("STRING", {"default": "1024x1024"}),
            },
        }

    RETURN_TYPES = ("INT", "INT",)
    RETURN_NAMES = ("WIDTH", "HEIGHT",)
    FUNCTION = "extract_size"
    CATEGORY = "EZ NODES"
    DESCRIPTION = "Extract the last 2 numbers found within a text string to be used as width and height."

    def extract_size(self, text_input):
        try:
            # Handle None or empty input
            if text_input is None or text_input == "":
                print("EZ_Text_to_Size: No input provided.")
                return (None)
            
            # Convert to string to ensure we're working with a string
            text_input = str(text_input)
            
            # Extract all numbers from the text using regex
            numbers = re.findall(r'\d+', text_input)
            
            # Check if we have at least 2 numbers
            if len(numbers) < 2:
                print(f"EZ_Text_to_Size: Need at least 2 numbers, found {len(numbers)} in '{text_input}'.")
                return (None)
            
            # Return last two numbers as width and height
            width = int(numbers[-2])
            height = int(numbers[-1])
            return (width, height,)
            
        except Exception as e:
            print(f"EZ_Text_to_Size: Error processing input '{text_input}': {str(e)}.")
            return (None)
