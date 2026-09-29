Table to be updated here. It is saved in notepad now
# MP1 Prompt Lab - Strategy Comparison 
## Comparison results

The four prompting strategies were evaluated on 10 job posting snipeets. Each strategy was tested on the same snippet using 'gpt-4o-mini' with 
temparature 0.0

| Strategy | Accurracy (mean of 3) | Parse Rate | Judge Score | Total Cost ($) | Latency p50 (s) |
| CoT      |  2.7                  | 1.0        | 3.9         | 0.0001         | 1.145           |
| Few-Shot | 2.9                   | 1.0        | 4.0         | 0.0001         | 1.209           |
| Structured| 2.7                  | 1.0        | 3.9         | 0.0001         | 1.044           |
| Zero-shot| 2.8                   | 1.0        |3.9          | 0.0001*        | 1.103           |

\* The displayed '$0.000' is rounded to 3 decimal places. The actual API cost is non zero

## Obervation 

- few shot achieved an average extarction accurancy of 2.9 out of 3 fields 
- Zero shot achieved an accuracy of 2.8 out of 3 
- Chain of thoughts and Structured prompting both achieved an average accuracy of 2.7 out of 3
- All 4 strategies achieved a 100% parse rate 
- Few-Shot received the highest averaage LLM judge score of 4 
- Zero shot, chain of thoughts and Structured received an average LLM score of 3.9 
- Structured prompting received the lowest median latency of 1.044 
- Total API cost for all 4 stragies are very small 

## Evaluation method 
The extraction model was 
- gpt-4o-mini
- temparature: '0.0' 

The LLM Judge was 
- gpt-4o
- temparature: '0.0'

Accuracy was calcualated by comparting 3 fields 
1. Company 
2. Role 
3. Years of Experience required 

Each field contributed one point, giving an accuracy score from 0 to 3 

The LLM used a 1-4 rurbric based on how many fields were correct and whether fabricated information was present 

Latency was reported using the median (p50) response time, and cost was calculated from the input and output token usage