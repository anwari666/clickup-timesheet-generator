# Clickup Timesheet Generator
This little script is made during my tenure at a consultation company. They required us to create a timesheet (basically a log-based time report) every month. Since our design team _independently_ uses ClickUp, we log the time there BUT having no budget from the office to pay for ClickUp sucks too. So I created this little script to generate the report automatically-ish, and most importantly, for free. Well it gets the job done, so yeah, I'm a tad bit happy.

<img src="https://github.com/anwari666/clickup-timesheet-generator/blob/main/clickup-timesheet-generator.gif" />

## Installation & running

Just clone the repository, and:

```bash
pip install -r requirements.txt
python generate-report.py
```

Tested on Mac. Can't say it's working on Windows...