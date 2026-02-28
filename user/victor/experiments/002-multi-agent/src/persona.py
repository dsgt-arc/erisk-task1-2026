import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel

# --- CONFIGURATION ---
BASE_MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct"

class Persona:
    def __init__(self, persona_id: int = 1):
        adapter_path = f"anxo/erisk26-task1-patient-{persona_id - 1:02d}-adapter"

         # 1. Load Tokenizer & Fix Padding
        self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID)
        self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
        self.tokenizer.padding_side = 'left' # Crucial for generation

        # 2. Load Base Model (Force float16 for compatibility)
        self.base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID,
            torch_dtype=torch.float16,
            device_map="auto",
        )

        # 3. Load the Patient Adapter
        print(f"Loading Adapter from {adapter_path}...")
        self.model = PeftModel.from_pretrained(self.base_model, adapter_path)

        # 4. Initialize History with the "Generic" Prompt
        # DO NOT CHANGE SYSTEM PROMPT. It is crucial for ensuring the patient behaves as intended.
        # Important: IT WILL BE CONSIDERED AS CHEATING!!
        self.messages = [
            {"role": "system", "content": "You are a simulated patient. Act realistically based on your internal training. Ensure contextual realism. Avoid overly detailed or formal speech. Keep natural speaking style (e.g., short answers, hesitations, casual expressions). Do not mention you are an AI."},
        ]

        self.terminators = [
            self.tokenizer.eos_token_id,
            self.tokenizer.convert_tokens_to_ids("<|eot_id|>")
        ]

        print("--- Patient Loaded. Type 'quit' to exit. ---")
    
    def chat(self, user_input):
        # 1. Update history
        self.messages.append({"role": "user", "content": user_input})

        # 2. Format history & Create Attention Mask
        # return_dict=True gives us the 'attention_mask' automatically
        inputs = self.tokenizer.apply_chat_template(
            self.messages,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True 
        ).to(self.model.device)

        # 3. Generate response
        # explicitly passing attention_mask prevents the warning you saw earlier
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=inputs.input_ids,
                attention_mask=inputs.attention_mask,
                max_new_tokens=256,
                eos_token_id=self.terminators,
                pad_token_id=self.tokenizer.eos_token_id,
                do_sample=True,
                temperature=0.6,
                top_p=0.9,
            )

        # 4. Decode response
        # We slice [input_len:] to ensure we don't print the prompt back to the user
        response_tokens = outputs[0][inputs.input_ids.shape[-1]:]
        assistant_text = self.tokenizer.decode(response_tokens, skip_special_tokens=True)

        print(f"Patient: {assistant_text}")

        # 5. Append assistant response to history
        self.messages.append({"role": "assistant", "content": assistant_text})

        return self.messages


if __name__ == "__main__":
    test_persona = Persona()

    while True:
        user_input = input("Doctor: ")
        if user_input.lower() == 'quit':
            break

        test_persona.chat(user_input)



    
    

    
