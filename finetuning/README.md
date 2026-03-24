<!-- ABOUT THE PROJECT -->
# Fine-tuning

Fine-tuning is the process of re-adjusting a base LLM model to improve its performance on a specific domain dataset. LLMs are trained on general knowledge datasets (Wikipedia, books, etc.) and thus have general understanding of the world around them. However, if we have specific needs (such as an LLM for a medical chatbot or for controlling a robot), we need to train the LLM with a more specific dataset to generate the desired output.

Below are the tools and methods used:
* The LLM model used is [Gemma 2B](https://huggingface.co/google/gemma-2b)
* The fine-tuning method used is Low Rank Adaptation [LoRA](https://arxiv.org/abs/2106.09685)
* The library for inference and fine-tuning is [Unsloth](https://github.com/unslothai/unsloth)

## Dataset

Before starting, we need to prepare a dataset. For the dataset format, I use the [Alpaca](https://github.com/gururise/AlpacaDataCleaned) format. This format is suitable because it consists of instruction, input, and output fields that provide sufficient information for the LLM to create an Action Plan. The instruction field contains instructions for the LLM to generate action plans (such as available functions, desired formats (JSON), and environmental constraints). The input field contains user commands (such as moving the robot arm forward), and the output field contains the expected Action Plan. Prompt engineering remains a hot and evolving topic. Although there is no one-size-fits-all method for creating good prompts, here are recommendations for prompting LLMs for robotics [GPT for Robotics](https://www.microsoft.com/en-us/research/uploads/prod/2023/02/ChatGPT___Robotics.pdf) that can be considered. An example of the dataset used is provided below.

```
"instruction":

"Objective: Your task is to generate a sequence of JSON responses to plan actions for a robot arm based on user input. If the objective cannot be achieved using the provided instructions and available objects, return an error message.

Provide a JSON object containing an array of "actions", identified with the key "actions".

Each action must be represented as an object with appropriate "command" and "parameters".

Available Objects and Coordinates (x,y,z):
1. Purple block = (-86.59, 117.21, -122.30)
2. Yellow block = (-168.94, -129.37, -68)
3. Blue block = (152.76, 158.92, 6)

Available Commands:
1. move: Move the robot arm in a certain direction. Include the "direction" parameter with values "atas" (up), "bawah" (down), "depan" (forward), "belakang" (backward), "kiri" (left), or "kanan" (right).
2. move_to: Move the robot arm to specific coordinates. Include "x", "y", and "z" parameters to specify the target coordinates.
3. suction_cup: Activate or deactivate the suction cup. Use the "action" parameter with values "on" or "off".
4. err_msg: Return an error message if the user's objective cannot be achieved with the current objects and commands. Use the "msg" parameter with value "tidak dapat membuat rencana aksi dengan kondisi terkini" (cannot create action plan with current conditions).

Example Command Usage:
"{"actions":[{"command":"move","parameters":{"direction":"atas"}},{"command":"move_to","parameters":{"x":-30.21,"y":233.32,"z":-40}},{"command":"suction_cup","parameters":{"action":"on"}},{"command":"err_msg","parameters":{"msg":"tidak dapat membuat rencana aksi dengan kondisi terkini"}}]}"

Usage Instructions:
1. To move an available object to specific coordinates, first activate the suction cup using the "suction_cup" command with "action" set to "on", then move to the object's coordinates using the "move_to" command.
2. Provide placement coordinates for the user's objective using the "move_to" command.
3. To release an object after using the suction cup, deactivate the suction cup first using the "suction_cup" command with "action" set to "off".
4. To move the robot laterally (for example, left, right, forward, backward, up, down), use the "move" command with the appropriate direction.
5. To move an object laterally (for example, left, right, forward, backward, up, down), first move the robot arm to the object's coordinates using the "move_to" command, then use the "move" command with the appropriate direction.
6. If the user's objective cannot be achieved with the current commands and objects, use the "err_msg" command.",

"input": "move the blue block position to the left",

"output": "{"actions": [{"command": "move_to", "parameters": {"x": 152.76, "y": 158.92, "z": 6}}, {"command": "suction_cup", "parameters": {"action": "on"}}, {"command": "move", "parameters": {"direction": "kiri"}}, {"command": "suction_cup", "parameters": {"action": "off"}}]}"

```

Here are important considerations:
* In real-world implementation, Available Objects and Coordinates will be injected in real-time through object detection. However, for fine-tuning purposes, they are kept static. If you want to use different objects, you can add them directly. Ensure that object coordinates are varied (not all integers or all positive numbers), because from experience, if coordinates are not varied, the LLM output may not be appropriate (for example, a coordinate of -210.32 might become 210 in the LLM's action plan because the coordinates lack variety).
* Make sure to create prompts that contain all necessary information. Remember, LLMs do not understand the actual environmental conditions, so ensure the prompt provides all required information. You may need to try several times until generating appropriate output. If using a different model (other than Gemma), don't forget to read the prompting/fine-tuning guide for that model.
* Create various input scenarios to improve model performance.

The complete dataset can be accessed at 🤗 (https://huggingface.co/datasets/Aryaduta/llm_robot)

## Fine-tuning

After preparing the dataset, we can perform fine-tuning. The fine-tuning method used is Low Rank Adaptation with the Unsloth library. It's important to note that for fine-tuning, ensure you have sufficient VRAM (in experiments on Google Colab free GPU, 14GB VRAM is more than enough for inference and fine-tuning). For the Unsloth library, at the time of writing, it is only available on Linux (Windows can use WSL). Unsloth provides example notebooks that can be run on Google Colab.

* The Unsloth repository can be accessed at 🦥 (https://github.com/unslothai/unsloth)

* The notebook used for fine-tuning can be accessed here: [Notebook](./train.ipynb)

Make sure to upload the dataset to Hugging Face to facilitate the fine-tuning process.

After fine-tuning, don't forget to save the model. For this research, the easiest way is to save only the LoRA adapter to a Hugging Face repository. If you want to save the full model (GGUF/llama.cpp), it will take longer and potentially timeout (if using free Colab). Complete guidelines are available in the example Colab notebook in the Unsloth repository.

Saving LoRA Adapter to Hugging Face:
```
model.push_to_hub_merged("hf/model", tokenizer, save_method = "lora", token = "")
```

When uploading the LoRA adapter to HF, the model will be saved in safetensor format. If you want to use Unsloth inference, you only need to call the adapter from HF (e.g., "aryaduta/model-finetune") in the model_name parameter.

An example of the inference code for the fine-tuned model will be discussed in the Implementation section.
