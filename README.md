# HUMAN-ROBOT INTERACTION BASED ON LARGE LANGUAGE MODEL FOR ACTION PLAN GENERATION ON ROBOTIC ARM.

This repository discusses research on how we can control a robotic arm (Dobot Magician) with natural language text input processed by a fine-tuned LLM to generate Low Level JSON Action Plans that will be executed by the robot in real time.

There are two parts to this project:
1. Fine-tuning the base LLM model. In this project, I use the Gemma model for LLM, Low Rank Adaptation (LoRA) for the fine-tuning method, and Unsloth for the inference and fine-tuning library.
2. Implementation with the robot. Simply put, the user will input natural language text which will then be sent to the LLM and will generate a Low Level JSON Action Plan. This JSON will be read and executed one by one.

For more information, open the README in the [Finetuning](./finetuning) and [Implementation](./implementasi) folders.
