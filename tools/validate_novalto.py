#!/usr/bin/env python3
"""
Novalto Dataset Validation Tool

This tool validates that a dataset file conforms to the expected Novalto format
for DPO training. It checks the JSON structure, field types, and data consistency.

Usage:
    python tools/validate_novalto.py <dataset_path>

Example:
    python tools/validate_novalto.py data/dataset.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from datasets import validate_dataset_file, NovaltoDataset


def main():
    """Main function for the validation tool."""
    parser = argparse.ArgumentParser(
        description="Validate a Novalto dataset file format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/validate_novalto.py data/dataset.json
  python tools/validate_novalto.py /path/to/my/dataset.json --verbose
  python tools/validate_novalto.py data/dataset.json --stats
        """
    )
    
    parser.add_argument(
        "dataset_path",
        help="Path to the dataset JSON file to validate"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed validation information"
    )
    
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Show dataset statistics"
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    if not Path(args.dataset_path).exists():
        print(f"Error: Dataset file not found: {args.dataset_path}", file=sys.stderr)
        sys.exit(1)
    
    try:
        if args.verbose:
            print(f"Validating dataset: {args.dataset_path}")
        
        # Validate the dataset
        is_valid = validate_dataset_file(args.dataset_path, "novalto")
        
        if is_valid:
            print(f"✓ Dataset is valid: {args.dataset_path}")
            
            # Show statistics if requested
            if args.stats:
                show_dataset_stats(args.dataset_path, args.verbose)
            
            sys.exit(0)
        else:
            print(f"✗ Dataset validation failed: {args.dataset_path}", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ Validation error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def show_dataset_stats(dataset_path: str, verbose: bool = False):
    """
    Show statistics about the dataset.
    
    Args:
        dataset_path: Path to the dataset file
        verbose: Whether to show detailed statistics
    """
    try:
        # Load the dataset using the Novalto implementation
        dataset = NovaltoDataset(dataset_path)
        data = dataset.load_data()
        
        print("\nDataset Statistics:")
        print("=" * 40)
        
        total_prompts = len(data)
        total_responses = sum(len(entry["responses"]) for entry in data.values())
        total_pairs = sum(len(entry["pairs"]) for entry in data.values())
        
        print(f"Total prompts: {total_prompts}")
        print(f"Total responses: {total_responses}")
        print(f"Total preference pairs: {total_pairs}")
        
        if total_prompts > 0:
            avg_responses = total_responses / total_prompts
            avg_pairs = total_pairs / total_prompts
            print(f"Average responses per prompt: {avg_responses:.2f}")
            print(f"Average preference pairs per prompt: {avg_pairs:.2f}")
        
        if verbose:
            print("\nDetailed Statistics:")
            print("-" * 20)
            
            # Response length statistics
            response_lengths = []
            prompt_lengths = []
            
            for prompt, entry in data.items():
                prompt_lengths.append(len(prompt))
                for response in entry["responses"]:
                    response_lengths.append(len(response))
            
            if response_lengths:
                print(f"Response length - Min: {min(response_lengths)}, Max: {max(response_lengths)}, Avg: {sum(response_lengths)/len(response_lengths):.1f}")
            
            if prompt_lengths:
                print(f"Prompt length - Min: {min(prompt_lengths)}, Max: {max(prompt_lengths)}, Avg: {sum(prompt_lengths)/len(prompt_lengths):.1f}")
            
            # Distribution of responses per prompt
            responses_per_prompt = [len(entry["responses"]) for entry in data.values()]
            if responses_per_prompt:
                from collections import Counter
                distribution = Counter(responses_per_prompt)
                print(f"\nResponses per prompt distribution:")
                for count, freq in sorted(distribution.items()):
                    print(f"  {count} responses: {freq} prompts")
            
            # Sample some prompts
            print(f"\nSample prompts (showing first 3):")
            for i, (prompt, entry) in enumerate(data.items()):
                if i >= 3:
                    break
                truncated_prompt = prompt[:100] + "..." if len(prompt) > 100 else prompt
                print(f"  {i+1}. {repr(truncated_prompt)}")
                print(f"     Responses: {len(entry['responses'])}, Pairs: {len(entry['pairs'])}")
        
    except Exception as e:
        print(f"Error generating statistics: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()