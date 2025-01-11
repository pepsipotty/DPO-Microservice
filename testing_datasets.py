import json
from preference_datasets import get_test_dataset, get_hh

def run_test(output_file="test_results.txt"):
    with open(output_file, "w") as f:

        def write_and_print(*args, **kwargs):
            print(*args, **kwargs)
            print(*args, **kwargs, file=f)


        write_and_print("Testing get_test_dataset")
        test_data = get_test_dataset()
        write_and_print("Test Dataset Output:")
        write_and_print(json.dumps(test_data, indent=2)) 

        write_and_print("\nTesting get_hh")
        hh_data = get_hh(split="test", silent=True)
        write_and_print("HH Dataset Output:")
        write_and_print(json.dumps(hh_data, indent=2))  

        write_and_print("\nVerifying structures")
        test_prompt_keys = list(test_data.keys())
        hh_prompt_keys = list(hh_data.keys())

        write_and_print(f"No of prompts in test dataset: {len(test_prompt_keys)}")
        write_and_print(f"Ni of prompts in hh dataset: {len(hh_prompt_keys)}")


if __name__ == "__main__":
    run_test()