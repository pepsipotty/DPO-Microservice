#!/bin/bash

# Set environment variables
export WANDB_DISABLED=true
export PYTHONPATH=/root/DPO-Microservice:$PYTHONPATH

# Change to the correct directory
cd /root/DPO-Microservice

# Run training with toy dataset using minimal parameters
python train.py \
    model=pythia28 \
    datasets=[novalto] \
    loss=dpo \
    loss.beta=0.1 \
    exp_name=toy_test_run \
    trainer=BasicTrainer \
    batch_size=1 \
    eval_batch_size=1 \
    gradient_accumulation_steps=1