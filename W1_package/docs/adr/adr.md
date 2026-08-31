AI Project Management Knowledge Assistant
__________________________________________

User Question
"What is the top-priority risk in Project ABC?"
Objective

The Agent should:
Retrieve the current risks for Project ABC.
Analyze probability, impact, age, dependencies and business impact.
Correlate risk information with project documents and relevant issues.
Identify the single highest-priority risk.
Explain why it is considered the top priority.
Provide supporting evidence
Recommend an action, while keeping the Project Manager as the final decision-maker.
___________________________________________

1. INPUTS — What goes in?
The Agent requires two categories of inputs.
A. User Input
Minimum input:
Project Name: Project ABC

Question:
"What is the top-priority risk in Project ABC?"

Time period: Current
Risk threshold: High
Project phase: Testing

B. Project Data
The Agent needs access to authorized project information.
Primary inputs
1. Risk Register
2. Project Status Reports
3. Meeting Minutes
4. Change Requests
5. Relevant JIRA Issues
6. Project Dependencies
 
2. TOOLS — What can the Agent call?

Tool 1 — Risk Retrieval
get_project_risks(project_id)
Example response:
Risk ID: R-001
Description: Data Migration Delay
Probability: High
Impact: High
Status: Open
Owner: Data Conversion Team 
Created: July 1

Tool 2 — Document Retrieval / RAG
search_project_documents(query)
Search:
Risk Register
Status Reports
Meeting Minutes
Project Plans
This helps to understand the context behind the risk.

Tool 3 — JIRA Search
search_jira(project_id, criteria)
Search for:
High priority issues
Blocked issues
Sev-1 / Sev-2 issues
Issues related to the risk

Tool 4 — Risk Scoring
Using Python:calculate_risk_score(probability, impact)
For example:
Probability = High
Impact      = High

Risk Score = 9/10
The exact scoring model should be defined for the above calculation 
Normalized Risk Score = (Probability × Impact / Max Risk score) × 10

Tool 5 — Current Date / Risk Age
For example:
calculate_risk_age(created_date, current_date)
This allows the system to determine:
Risk created: July 1
Current date: August 18

Age = 48 days

3. MEMORY — What does it remember?

Knowledge storage

Use two different mechanisms:

Project knowledge can be taken from Vector database and Structure Database 
    Vector database (RAG)- Refer Documents, Reports, MOM
    Structured database - Refer Risk, probability, Impact, Onwer, Status

RAG / Vector Database

Store:
Project documents
Status reports
Meeting minutes
Requirements
Change documentation

Structured Database

Store:
Risk ID
Project ID
Risk description
Probability
Impact
Risk score
Status
Owner
Created date
Target date
Mitigation
Dependencies

4. OUTPUT — What comes out?

Recommended output
PROJECT ABC — TOP PRIORITY RISK
Risk ID: R-001
Risk: Data Migration Delay

Priority: HIGH 🔴
Probability: HIGH
Impact: HIGH
Risk Score: 9/10
Status: OPEN
Age: 48 days
Owner: Data Migration Team

Why is this the top priority?
This risk has been identified as high probability and high impact. It is also affecting the downstream performance testing milestone.

Potential Project Impact:

• Performance testing may be delayed
• UAT start date may be affected
• Production release may move
• Additional testing resources may be required

Recommended Action:

Escalate the migration dependency and establish a
recovery plan with the Data Migration Team.

Evidence:

[Risk Register – R-001]
[Weekly Status Report – Aug 14]
[Meeting Minutes – Aug 15]
[JIRA ABC-1234]

5. AUTONOMY LEVEL — How much can it act?

The Agent to:

✓ Retrieve risks
✓ Analyze risks
✓ Rank risks
✓ Identify the top risk
✓ Explain the reasoning
✓ Search supporting evidence
✓ Recommend actions
✓ Generate reports

But it cannot:

✗ Change risk priority
✗ Change risk status
✗ Assign an owner
✗ Close the risk
✗ Modify project dates
✗ Create a JIRA ticket
✗ Send an escalation email
✗ Approve a Change Request

The workflow is:

User
  │
  ▼
AI Agent
  │
  ▼
Retrieve Information
  │
  ▼
Analyze Risks
  │
  ▼
Identify Top Risk
  │
  ▼
Recommend Action
  │
  ▼
Project Manager
  │
  ▼
Human Decision

This is Human-in-the-Loop.

6. DECISION BOUNDARIES — What's off-limits?

Boundary 1 — No hallucination

Should not invent a risk.

If AI cannot find sufficient evidence, provide comments as follows: 
"I cannot determine the top-priority risk because there is insufficient current risk information for
Project ABC."
It should not guess.

Boundary 2 — Evidence required

Every important factual claim must be supported by project data.

For example:
"R-001 is the highest-priority risk."
AI should be able to show:

Risk Register
+
Status Report
+
Relevant JIRA issues

7. SUCCESS METRICS — How do we know it works?

Eight Production KPIs are incorporated below  

Task success
Grounded response
Hallucination rate
Retrieval hit rate
Tool success rate
Cost per query
Latency P50/P95
Escalation rate

KPI 1 — Task Success
Question

Did the AI correctly identify the top-priority risk?

Example:
Expected:
R-001

AIt:
R-001

Result:
PASS
Target
≥ 95% task success

KPI 2 — Grounded Response
Question

Is the answer backed by project sources?

If AI says:

"R-001 has been open for 48 days."
There must be evidence supporting the claim.

Target
≥ 98% grounded responses

For a controlled capstone dataset:
Target = 100%

KPI 3 — Hallucination Rate

The system should not hallucinate.

Measure:

Hallucination Rate =
Unsupported factual claims
──────────────────────────── × 100
Total factual claims
Target

0% hallucination on the golden test dataset

For production, we cann establish a slightly less strict operational target such as:

<1–2%, with all high-risk hallucinations treated as failures.

For capstone:
Target = 0%

KPI 4 — Retrieval Hit Rate

This measures:
Did the system retrieve the correct documents/data needed to answer the question?
For example, the correct sources may be:

✓ Risk Register
✓ Latest Status Report
✓ Recent Meeting Minutes
✓ Relevant JIRA issue
Target

≥ 95% retrieval hit rate

KPI 5 — Tool Success Rate

This refers to tools  

For example:
get_project_risks()
search_project_documents()
search_jira()
calculate_risk_score()

Measure:

Successful tool calls
───────────────────── × 100
Total tool calls
Target

≥ 99% tool success rate

A failed JIRA call should not silently result in the AI inventing information.

Instead:

"JIRA data could not be retrieved, so I cannot use current JIRA information in this assessment."

KPI 6 — Cost per Query

Every Agent interaction can have a cost because of:

LLM tokens
Embedding calls
Tool calls
Vector database usage

Track:

Cost per query
For example:
Average cost/query = $0.01
we should establish the actual target after you select the model and infrastructure.

For capstone:

Target: Define a maximum acceptable cost/query and monitor it for every run.
LLM APIs — tokens, cost and latency.

KPI 7 — Latency P50 / P95

Latency = 10 seconds

I recommend defining this as:

Target

P95 end-to-end latency ≤ 10 seconds

This means 95% of requests should complete within 10 seconds.

Track both:

P50 = median response time
P95 = 95th percentile response time

Example:

P50 = 1.2 seconds
P95 = 10.0 seconds


PASS

KPI 8 — Escalation Rate

This measures:
How often does the AI need to hand the task to a human?

For example:

100 questions
   ↓
90 answered successfully
10 escalated

Escalation rate:

10%

Escalation is good when the AI lacks sufficient evidence or the decision is high-risk.

For example:

Insufficient evidence
       ↓
Human escalation

is preferable to:

Insufficient evidence
       ↓
AI  guesses
       ↓
Hallucination

Final Seven-Field Solution Framing Canvas

Field	Project ABC — Top Priority Risk Agent
1. Inputs	User question + Project ID + Risk Register + Status Reports + Meeting Minutes + relevant JIRA/issues
2. Tools	Risk Retrieval + RAG/Document Search + JIRA Search + Risk Scoring + Date/Age Calculation
3. Memory: RAG/Vector DB stores project documents; Structured DB stores risk information
4. Outputs	Top-priority risk + risk score + probability + impact + status + age + project impact + evidence + recommended action; optional visual risk dashboard
5. Autonomy Level	Suggest Only — Agent analyzes and recommends; Project Manager makes the final decision
6. Decision Boundaries	No hallucination; no unsupported claims; only authorized data; no autonomous changes to risks/JIRA/schedule; human approval required for actions
7. Success Metrics	Task success ≥95%; Grounded response ≥98%; Hallucination = 0% on golden dataset; Retrieval hit rate ≥95%; Tool success ≥99%; Cost/query monitored; P95 latency ≤2 sec; Escalation monitored




