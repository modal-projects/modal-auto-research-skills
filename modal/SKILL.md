---
name: modal
description: >
  This skill provides guidance for building and deploying applications on the
  Modal cloud platform. Use this skill whenever the user mentions Modal or has
  Python code that imports the `modal` SDK. This skill should also trigger when
  the user needs to run Python code with horizontal scalability (e.g. batch
  jobs), needs access to GPUs (e.g. AI/ML workloads including training and
  inference) or needs to execute processes in a sandboxed environment.
---

# Overview

This skill provides high-level guidance for working with the Modal cloud platform.

Modal is a platform for AI / ML workloads. It offers highly-scalable serverless compute (including GPUs) with minimal configuration.

# Documentation

Modal's documentation is outlined at https://modal.com/llms.txt.

The docs are divided into three sections:

- Fetch _Guide_ pages for in-depth explanations of Modal features, primitives, and workflows
- Fetch _Examples_ pages to see how different AI applications look on Modal
- Fetch _API Reference_ pages for signatures and docstrings for components of the Python SDK

For broader context, https://modal.com/llms-full.txt aggregates all docs in a single very large file. Do not read this into your main context.

# Getting up to date

You have significant knowledge about Modal from your training data but may not be aware of new features or recent changes to the API. Fetching relevant docs while planning can help you discover the most up-to-date way to accomplish a task on Modal.

The Modal CLI provides a `modal changelog` command that can also be useful for learning about recent changes. There are several options for querying change sets. E.g., running `modal changelog --since DATE` will show all changes made between that date (e.g., your knowledge cutoff) and the release of the SDK version that is in use.

Run `modal --version` to see the SDK version that is in use. Note that the online docs may reference features that are available only in recent SDKs.

# Using the CLI

The `modal` CLI can be used to run or deploy code, manage resources, and observe running Apps. It is a key tool for interacting with Modal.

Run `modal --help` to see all available CLI commands.

You can see more detailed information about each command by running `modal [command] --help`. If you are unsure of how to accomplish a task through the CLI (or if you get an error when trying), read the `--help` rather than guessing.

Tip: most CLI commands accept a `--json` flag to make their output more easily parseable, e.g. with `jq`.

# More information

When authoring Modal App code, the following references will be useful:

- ./references/app-structure.md
- ./references/function-types.md
- ./references/development-workflow.md
