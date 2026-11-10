# The Ice Scraper - Troy Hack 2026
**An automated document review tool for identifying potentially sensitive content in documents.**

*Created by [@atticuscornett](https://github.com/atticuscornett), [@CL-16](https://github.com/CL-16), and [@Pokeplush12](https://github.com/Pokeplush12)*

*This project was created for Troy Hack 2026, a 24-hour hackathon hosted by Troy University. It received 3rd place in the competition.*


## Table of Contents
- [Objective](#objective)
- [Features](#features)
- [Program Design](#program-design)
- [Detection Techniques](#detection-techniques)
- [Running](#running)

## Objective

The Ice Scraper is a tool that scans documents for topics that may need to be redacted before being shared with the public.
It does not make the final decision on whether a document is ready to publish or not. Rather, it is a tool that 
aims to streamline and assist the review process by identifying which documents and what parts are most likely to need extra attention.

## Features

### Issue Highlighting
Ice Scraper identifies and highlights potentially sensitive content and provides a list of issues for the user to review.
The highlights panel allows the user to remove false positives and the preview is updated in real time to reflect the changes.
High-confidence primary issues are highlighted in red, while secondary possible issues are highlighted in yellow.

### Quick Navigation
The highlights panel also identifies the type of issues that were found, and clicking on the issue will jump straight to that part of the document.
This adds additional convenience and efficiency to the review process.

### Document Triage 
Documents that have not been reviewed yet appear at the top of the documents list.
Documents that have been reviewed are moved to the bottom of the list and show their approval status.
All documents show their processing status, and the color of the document title indicates the highest severity of issues found in that document.

### Batch Processing
The Ice Scraper can import and process multiple documents at once, allowing for faster review of large batches of documents.
Job processing and queuing is done in the background, allowing the user to continue reviewing documents while new ones are being processed.
The program supports both PDF and Word documents.

### Fully Offline
Ice Scraper can be used fully offline (after it is run online at least once to install models) by setting the following environment variables before running:
```shell
set HF_HUB_OFFLINE=1
set HF_DATASETS_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
```
This allows critical data to stay on device, never touching the cloud, ensuring sensitive information doesn't leave the host machine.

## Program Design
![Program Modules](./diagrams/program_modules.png)

### System Modularity
The Ice Scraper is designed with modularity in mind, which allowed for easier collaboration during the hackathon,
but also allows for easier maintenance and future development.
The program is divided into two main sections: the GUI logic loop and the job logic loop, with a job dispatcher acting as a middleman between them.
The front-end of the GUI provides a web-based interface for users to easily interact with the program and organize and triage issues with documents.
The Python back-end of the GUI loop passes requests to the job dispatcher and receives results back to display to the user.
The job dispatcher maintains the status of all the requested jobs and creates new jobs on new threads upon request.
The job logic loop handles the actual document processing and issue detection, with modules for each list of rules.
Additional modules can easily be added to the job logic loop to expand the program's capabilities.


![Module Functions](./diagrams/module_functions.png)
### Module Functions
Modules are further broken down into individual functions for each rule.
Each function checks for violations of a specific rule and adds to the list of issues if one is found.
Because each rule is its own function, different rules can use the best detection technique for its specific task.
This allows for greater expandability with new rules in the future, as well as allowing for a better balance between accuracy and performance.

## Detection Techniques
![Detection Techniques](./diagrams/decision_tree.png)

Issues are detected using a combination of techniques, generally preferring a balance of accuracy and performance.
The diagram above shows the decision tree determining which detection technique should be used for each rule.
Because the rules are broken down into individual functions, each rule can utilize the best detection technique for its specific task.

The detection techniques used are:
- Classifier models
- Semantic similarity (using a text embedding model)
- Regular expressions

### Classifier Models
OpenAI's PII classifier model, `"openai/privacy-filter"`, is used to detect sentences that contain personally identifiable information (PII).
This model is reasonably accurate and fast, making it a good choice for this specific task.
Additionally, the model identifies the type of PII that was found, allowing for issues to have more specific information.
Classifiers are the most preferred detection technique because they are most accurate, but they are limited to the 
topics they are trained on, so they cannot be used for most rules.

### Semantic Similarity
Semantic similarity is used to detect sentences that are similar in topic or meaning to a list of sensitive topics.
The model used is `"BAAI/bge-base-en-v1.5"`, which is a text embedding model used to convert sentences into vectors.
The similarity is then determined using cosine similarity, and if the similarity is above a certain threshold, it is considered a match.
If a high-confidence match is found, the sentence is added to the list of issues with the topic that it was found to be similar to.
If a medium-confidence match is found, the sentence is also compared to a list of known topic keywords, and if a match is found, it is added to the list of issues.
Most rules use semantic similarity because it is more accurate than regular expressions and can be used for a wider range of topics than classifiers.

### Regular Expressions
Regular expressions are used only when a rule expects a specific format.
They are the fastest of the three detection techniques, but they are also the least accurate and most rigid.
This can lead to many false positives and false negatives, so they are avoided unless they are particularly well-suited for a rule.


## Running

1. Clone the repository to your local machine
2. Install Python if it is not already installed (tested with Python 3.15.2)
3. Install the required dependencies using pip
    ```shell
    pip install -r requirements.txt
    ```
4. Run the application
   - Note: The Ice Scraper must be run online at least once to install the required models from Hugging Face.
     After first run, the program can be run fully offline (see Features section for instructions).
   ```shell
    python main.py
    ```