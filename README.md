# ComfyUI-EZ-AF-Nodes

**Custom nodes pack for ComfyUI**

This custom nodes pack helps to conveniently control text in complex prompt-builder type workflows

> [!WARNING]
> This pack requires pysssss.Binding extension. To use it, install [pythongosssss Custom Scripts](https://github.com/pythongosssss/ComfyUI-Custom-Scripts)

<!--  It is recommended to install this pack using [ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager)  --> 


## Nodes

### EZ CSV Reader

![CSV Reader](https://github.com/user-attachments/assets/b17f8e55-9761-4b66-93bd-acd438bee866)

This node allows you to import positive and negative prompts from a selected line of selected .csv file

Files are located in **...\ComfyUI\custom_nodes\ComfyUI-EZ-AF-Nodes\CSV**

- You can add your own files
- Node supports sub-directories
- You can keep LORA weights and wildcards in prompts saved in .csv

> [!NOTE]
> .csv files for this node use **semicolon** delimeters, native to Microsoft Excel
> 
> Quotations marks are not needed (as prompts generally shouldn't contain semicolons), but allowed

### EZ MEGA Text Concatenate

![Concatenate](https://github.com/user-attachments/assets/1179f642-8b28-4c50-9850-71df8ac974cf)

This node allows you to concatenate up to **24** strings of text

Useful for extremely complex prompt-builder workflows.

No more concat stacking!

### EZ String

![String](https://github.com/user-attachments/assets/9e0c9455-a9ce-4617-9847-e1cb2f2e6b6d)

This node works like a string primitive, but allows you to output text as _"ANY"_ type

This is primarily useful to easily create inputs for _"COMBO"_ type widgets.

No more unnecessary conversions!


## Example

Drag and Drop this image (or this [code](https://github.com/ez-af/ComfyUI-EZ-AF-Nodes/blob/main/examples/workflow.json)) into your ComfyUI window to see example workflow with some tips:

![Example Workflow](https://github.com/ez-af/ComfyUI-EZ-AF-Nodes/blob/main/examples/Workflow.png)

@ez-af

[ComfyUI-EZ-AF-Nodes](https://github.com/ez-af/ComfyUI-EZ-AF-Nodes)
