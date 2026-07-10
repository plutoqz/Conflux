<!-- source: https://en.wikipedia.org/wiki/Prompt_engineering -->
# Prompt engineering

> Source: https://en.wikipedia.org/wiki/Prompt_engineering
> License: CC BY-SA 4.0 (Wikipedia)

From Wikipedia, the free encyclopedia
Structuring text as input to generative artificial intelligence
Prompt engineeringis the process of structuringnatural languageinputs(known asprompts) to produce specified outputs from agenerative artificial intelligence(GenAI) model.Context engineeringis the related area ofsoftware engineeringthat focuses on the management of non-prompt and prompt contexts supplied to the GenAI model, such as system instructions,metadata,APItools and tokens.

Prompt engineering
is the process of structuring
natural language
inputs
(known as
prompts
) to produce specified outputs from a
generative artificial intelligence
(GenAI) model.
Context engineering
is the related area of
software engineering
that focuses on the management of non-prompt and prompt contexts supplied to the GenAI model, such as system instructions,
metadata
,
API
tools and tokens.
It can also be defined as the practice of designing and refining input instructions given to a generative AI model to produce more accurate, relevant, or useful outputs. Effective prompt engineering involves understanding how a model interprets language, and may include techniques such as few-shot prompting, chain-of-thought prompting, and role assignment. It is increasingly considered a skill for working withlarge language models(LLMs) in both research and professional contexts.

It can also be defined as the practice of designing and refining input instructions given to a generative AI model to produce more accurate, relevant, or useful outputs. Effective prompt engineering involves understanding how a model interprets language, and may include techniques such as few-shot prompting, chain-of-thought prompting, and role assignment. It is increasingly considered a skill for working with
large language models
(LLMs) in both research and professional contexts.
During the 2020sAI boom, prompt engineering became regarded as a business capability across corporations and industries. Employees with the titleprompt engineerwere hired to create prompts that would increase productivity and efficacy, although the individual title has since lost traction amid AI models that produce better prompts than humans and corporate training in prompting for general employees.

During the 2020s
AI boom
, prompt engineering became regarded as a business capability across corporations and industries. Employees with the title
prompt engineer
were hired to create prompts that would increase productivity and efficacy, although the individual title has since lost traction amid AI models that produce better prompts than humans and corporate training in prompting for general employees.
Common prompting techniques include multi-shot, chain-of-thought, and tree-of-thought prompting, as well as assigning roles to the model. Automated prompt generation methods, such asretrieval-augmented generation(RAG), provide for greater accuracy and a wider scope of functions for prompt engineers.Prompt injectionis a type ofcybersecurityattack that targetsmachine learningmodels through malicious prompts.

Common prompting techniques include multi-shot, chain-of-thought, and tree-of-thought prompting, as well as assigning roles to the model. Automated prompt generation methods, such as
retrieval-augmented generation
(RAG), provide for greater accuracy and a wider scope of functions for prompt engineers.
Prompt injection
is a type of
cybersecurity
attack that targets
machine learning
models through malicious prompts.

## Terminology

Terminology
[
edit
]
The Oxford English Dictionary defines prompt engineering as "The action or process of formulating and refining prompts for anartificial intelligenceprogram, algorithm, etc., in order to optimize its output or to achieve a desired outcome; the discipline or profession concerned with this."[1]In 2023, prompt ("an instruction given to an artificial intelligence program, algorithm, etc., which determines or influences the content it generates") was the runner-up to Oxford'sword of the year.[2]

The Oxford English Dictionary defines prompt engineering as "The action or process of formulating and refining prompts for an
artificial intelligence
program, algorithm, etc., in order to optimize its output or to achieve a desired outcome; the discipline or profession concerned with this."
[
1
]
In 2023, prompt ("an instruction given to an artificial intelligence program, algorithm, etc., which determines or influences the content it generates") was the runner-up to Oxford's
word of the year
.
[
2
]

### Prompt

Prompt
[
edit
]
A prompt is somenatural languagetext that describes and prescribes the task that an artificial intelligence (AI) should perform.[3]A prompt for a text-to-textlanguage modelcan be a query, acommand, or a longer statement referencing context,instructions, and conversation history. The process of prompt engineering may involve designing clear queries, refining wording, providing relevant context, specifying the style of output, and assigning a character for the AI to mimic in order to guide the model toward more accurate, useful, and consistent responses.[4][5]

A prompt is some
natural language
text that describes and prescribes the task that an artificial intelligence (AI) should perform.
[
3
]
A prompt for a text-to-text
language model
can be a query, a
command
, or a longer statement referencing context,
instructions
, and conversation history. The process of prompt engineering may involve designing clear queries, refining wording, providing relevant context, specifying the style of output, and assigning a character for the AI to mimic in order to guide the model toward more accurate, useful, and consistent responses.
[
4
]
[
5
]
When communicating with atext-to-imageor a text-to-audio model, a typical prompt contains a description of a desired output such as "a high-quality photo of an astronaut riding a horse"[6]or "Lo-fi slow BPM electro chill with organic samples".[7]Prompt engineering may be applied to text-to-image models to achieve a desired subject, style, layout, lighting, and aesthetic.[8]

When communicating with a
text-to-image
or a text-to-audio model, a typical prompt contains a description of a desired output such as "a high-quality photo of an astronaut riding a horse"
[
6
]
or "Lo-fi slow BPM electro chill with organic samples".
[
7
]
Prompt engineering may be applied to text-to-image models to achieve a desired subject, style, layout, lighting, and aesthetic.
[
8
]

### Techniques

Techniques
[
edit
]
Common terms used to describe various specific prompt engineering techniques includechain-of-thought,[9]tree-of-thought,[10]andretrieval-augmented generation(RAG).[11]A 2024 survey of the field identified over 50 distinct text-based prompting techniques, 40 multimodal variants, and a vocabulary of 33 terms used across prompting research, highlighting a present lack of standardised terminology for prompt engineering.[12]

Common terms used to describe various specific prompt engineering techniques include
chain-of-thought
,
[
9
]
tree-of-thought
,
[
10
]
and
retrieval-augmented generation
(RAG).
[
11
]
A 2024 survey of the field identified over 50 distinct text-based prompting techniques, 40 multimodal variants, and a vocabulary of 33 terms used across prompting research, highlighting a present lack of standardised terminology for prompt engineering.
[
12
]
Vibe codingis anAI-assisted software developmentmethod where a user prompts an LLM with a description of what they want and lets it generate or edit the code. In 2025, "vibe coding" was theCollins Dictionaryword of the year.[13]

Vibe coding
is an
AI-assisted software development
method where a user prompts an LLM with a description of what they want and lets it generate or edit the code. In 2025, "vibe coding" was the
Collins Dictionary
word of the year.
[
13
]

### Context engineering

Context engineering
[
edit
]
Context engineeringis a related process that focuses on the context elements that accompany user prompts, which include system instructions, retrieved knowledge, tool definitions, conversation summaries, and task metadata. Context engineering is performed to improve reliability, provenance and token efficiency inproductionLLM systems.[14][15]The concept emphasises operational practices such as token budgeting, provenance tags, versioning of context artifacts, observability (logging which context was supplied), and context regression tests to ensure that changes to supplied context do not silently alter system behaviour.[16]

Context engineering
is a related process that focuses on the context elements that accompany user prompts, which include system instructions, retrieved knowledge, tool definitions, conversation summaries, and task metadata. Context engineering is performed to improve reliability, provenance and token efficiency in
production
LLM systems.
[
14
]
[
15
]
The concept emphasises operational practices such as token budgeting, provenance tags, versioning of context artifacts, observability (logging which context was supplied), and context regression tests to ensure that changes to supplied context do not silently alter system behaviour.
[
16
]

## Rationale

Rationale
[
edit
]
Research has found that the performance oflarge language models(LLMs) is highly sensitive to choices such as the ordering of examples, the quality of demonstration labels, and even small variations in phrasing. In some cases, reordering examples in a prompt produced accuracy shifts of more than 40 percent.[12]

Research has found that the performance of
large language models
(LLMs) is highly sensitive to choices such as the ordering of examples, the quality of demonstration labels, and even small variations in phrasing. In some cases, reordering examples in a prompt produced accuracy shifts of more than 40 percent.
[
12
]

### In-context learning

In-context learning
[
edit
]
A model's ability to temporarily learn from prompts is known asin-context learning. In-context learning is anemergent ability[17]of large language models. It is an emergent property of model scale, meaning that breaks inscaling lawsoccur, leading to its efficacy increasing at a different rate in larger models than in smaller models.[17][18]Unlike training andfine-tuning, which produce lasting changes, in-context learning is temporary.[19]Training models to perform in-context learning can be viewed as a form ofmeta-learning, or "learning to learn".[20]

A model's ability to temporarily learn from prompts is known as
in-context learning
. In-context learning is an
emergent ability
[
17
]
of large language models. It is an emergent property of model scale, meaning that breaks in
scaling laws
occur, leading to its efficacy increasing at a different rate in larger models than in smaller models.
[
17
]
[
18
]
Unlike training and
fine-tuning
, which produce lasting changes, in-context learning is temporary.
[
19
]
Training models to perform in-context learning can be viewed as a form of
meta-learning
, or "learning to learn".
[
20
]

### Prompting to estimate model sensitivity

Prompting to estimate model sensitivity
[
edit
]
Research consistently demonstrates that LLMs are highly sensitive to subtle variations in prompt formatting, structure, and linguistic properties. Some studies have shown up to 76 accuracy points across formatting changes in few-shot settings.[21]Linguistic features significantly influence prompt effectiveness—such as morphology, syntax, and lexico-semantic changes—which meaningfully enhance task performance across a variety of tasks.[5][22]Clausal syntax, for example, improves consistency and reduces uncertainty in knowledge retrieval.[23]This sensitivity persists even with larger model sizes, additional few-shot examples, or instruction tuning.

Research consistently demonstrates that LLMs are highly sensitive to subtle variations in prompt formatting, structure, and linguistic properties. Some studies have shown up to 76 accuracy points across formatting changes in few-shot settings.
[
21
]
Linguistic features significantly influence prompt effectiveness—such as morphology, syntax, and lexico-semantic changes—which meaningfully enhance task performance across a variety of tasks.
[
5
]
[
22
]
Clausal syntax, for example, improves consistency and reduces uncertainty in knowledge retrieval.
[
23
]
This sensitivity persists even with larger model sizes, additional few-shot examples, or instruction tuning.
To address sensitivity of models and make them more robust, several evaluative methods have been proposed. FormatSpread facilitates systematic analysis by evaluating a range of plausible prompt formats, offering a more comprehensive performance interval.[21]Similarly, PromptEval estimates performance distributions across diverse prompts, enabling robust metrics such as performance quantiles and accurate evaluations under constrained budgets.[24]

To address sensitivity of models and make them more robust, several evaluative methods have been proposed. FormatSpread facilitates systematic analysis by evaluating a range of plausible prompt formats, offering a more comprehensive performance interval.
[
21
]
Similarly, PromptEval estimates performance distributions across diverse prompts, enabling robust metrics such as performance quantiles and accurate evaluations under constrained budgets.
[
24
]

## Prompting techniques

Prompting techniques
[
edit
]

### Multi-shot

Multi-shot
[
edit
]
A prompt may include a few examples for a model to learn from in-context, an implementation offew-shot learningfor LLMs.[9][25][26]For example, the prompt may ask the model to complete "maison→ house,chat→ cat,chien→", with the expected response beingdog.[27]

A prompt may include a few examples for a model to learn from in-context, an implementation of
few-shot learning
for LLMs.
[
9
]
[
25
]
[
26
]
For example, the prompt may ask the model to complete "
maison
→ house,
chat
→ cat,
chien
→", with the expected response being
dog.
[
27
]

### Chain-of-thought

Chain-of-thought
[
edit
]
See also:
Reflection (artificial intelligence)
Chain-of-thought(CoT) prompting is a technique that allowslarge language models(LLMs) to solve a problem as a series of intermediate steps before giving a final answer. In 2022,Google Brainreported that chain-of-thought prompting improvesreasoningability by inducing the model to answer a multi-step problem with steps of reasoning that mimic atrain of thought.[9][28]Chain-of-thought techniques were developed to help LLMs handle multi-step reasoning tasks, such asarithmeticorcommonsense reasoningquestions.[29][30]

Chain-of-thought
(CoT) prompting is a technique that allows
large language models
(LLMs) to solve a problem as a series of intermediate steps before giving a final answer. In 2022,
Google Brain
reported that chain-of-thought prompting improves
reasoning
ability by inducing the model to answer a multi-step problem with steps of reasoning that mimic a
train of thought
.
[
9
]
[
28
]
Chain-of-thought techniques were developed to help LLMs handle multi-step reasoning tasks, such as
arithmetic
or
commonsense reasoning
questions.
[
29
]
[
30
]
When applied toPaLM, a 540 billion parameterlanguage model, according to Google, CoT prompting significantly aided the model, allowing it to perform comparably with task-specificfine-tunedmodels on several tasks, achievingstate-of-the-artresults at the time on the GSM8Kmathematical reasoningbenchmark.[9]It is possible to fine-tune models on CoT reasoning datasets to enhance this capability further and stimulate betterinterpretability.[31][32]

When applied to
PaLM
, a 540 billion parameter
language model
, according to Google, CoT prompting significantly aided the model, allowing it to perform comparably with task-specific
fine-tuned
models on several tasks, achieving
state-of-the-art
results at the time on the GSM8K
mathematical reasoning
benchmark
.
[
9
]
It is possible to fine-tune models on CoT reasoning datasets to enhance this capability further and stimulate better
interpretability
.
[
31
]
[
32
]
As originally proposed by Google,[9]each CoT prompt is accompanied by a set of input/output examples—calledexemplars—to demonstrate the desired model output, making it afew-shotprompting technique. However, according to a later paper from researchers at Google and theUniversity of Tokyo, simply appending the words "Let's think step-by-step"[33]was also effective, which allowed for CoT to be employed as azero-shottechnique.

As originally proposed by Google,
[
9
]
each CoT prompt is accompanied by a set of input/output examples—called
exemplars
—to demonstrate the desired model output, making it a
few-shot
prompting technique. However, according to a later paper from researchers at Google and the
University of Tokyo
, simply appending the words "Let's think step-by-step"
[
33
]
was also effective, which allowed for CoT to be employed as a
zero-shot
technique.

#### Self-consistency

Self-consistency
[
edit
]
Self-consistencyperforms several chain-of-thought rollouts, then selects the most commonly reached conclusion out of all the rollouts.[34][35]

Self-consistency
performs several chain-of-thought rollouts, then selects the most commonly reached conclusion out of all the rollouts.
[
34
]
[
35
]

### Tree-of-thought

Tree-of-thought
[
edit
]
Tree-of-thoughtprompting generalizes chain-of-thought by generating multiple lines of reasoning in parallel, with the ability to backtrack or explore other paths. It can usetree search algorithmslikebreadth-first,depth-first, orbeam.[10]

Tree-of-thought
prompting generalizes chain-of-thought by generating multiple lines of reasoning in parallel, with the ability to backtrack or explore other paths. It can use
tree search algorithms
like
breadth-first
,
depth-first
, or
beam
.
[
10
]

### Text-to-image prompting

Text-to-image prompting
[
edit
]
See also:
Artificial intelligence visual art § Prompt engineering and sharing
, and
Artificial intelligence visual art
In 2022,text-to-imagemodels likeDALL-E 2,Stable Diffusion, andMidjourneywere released to the public. These models take text prompts as input and use them to generate images.[36][8]Early text-to-image models typically do not understand negation, grammar and sentence structure in the same way aslarge language models, and may thus require a different set of prompting techniques. The prompt "a party with no cake" may produce an image including a cake.[37]

In 2022,
text-to-image
models like
DALL-E 2
,
Stable Diffusion
, and
Midjourney
were released to the public. These models take text prompts as input and use them to generate images.
[
36
]
[
8
]
Early text-to-image models typically do not understand negation, grammar and sentence structure in the same way as
large language models
, and may thus require a different set of prompting techniques. The prompt "a party with no cake" may produce an image including a cake.
[
37
]
Demonstration of the effect of negative prompts on images generated with
Stable Diffusion
Top
: no negative prompt
Centre
: "green trees"
Bottom
: "round stones, round rocks"
A text-to-image prompt commonly includes a description of the subject of the art, the desired medium (such asdigital paintingorphotography), style (such ashyperrealisticorpop-art), lighting (such asrim lightingorcrepuscular rays), color, and texture.[38]Word order also affects the output of a text-to-image prompt. Words closer to the start of a prompt may be emphasized more heavily.[39]

A text-to-image prompt commonly includes a description of the subject of the art, the desired medium (such as
digital painting
or
photography
), style (such as
hyperrealistic
or
pop-art
), lighting (such as
rim lighting
or
crepuscular rays
), color, and texture.
[
38
]
Word order also affects the output of a text-to-image prompt. Words closer to the start of a prompt may be emphasized more heavily.
[
39
]

#### Artist styles

Artist styles
[
edit
]
Some text-to-image models are capable of imitating the style of particular artists by name. For example, the phrasein the style of Greg Rutkowskihas been used in Stable Diffusion and Midjourney prompts to generate images in the distinctive style of Polish digital artistGreg Rutkowski.[40]Famous artists such asVincent van GoghandSalvador Dalíhave also been used for styling and testing.[41]

Some text-to-image models are capable of imitating the style of particular artists by name. For example, the phrase
in the style of Greg Rutkowski
has been used in Stable Diffusion and Midjourney prompts to generate images in the distinctive style of Polish digital artist
Greg Rutkowski
.
[
40
]
Famous artists such as
Vincent van Gogh
and
Salvador Dalí
have also been used for styling and testing.
[
41
]

#### Textual inversion and embeddings

Textual inversion and embeddings
[
edit
]
For text-to-image models,textual inversionperforms an optimization process to create a newword embeddingbased on a set of example images. This embedding vector acts as a "pseudo-word" which can be included in a prompt to express the content or style of the examples.[42]

For text-to-image models,
textual inversion
performs an optimization process to create a new
word embedding
based on a set of example images. This embedding vector acts as a "pseudo-word" which can be included in a prompt to express the content or style of the examples.
[
42
]

### Image prompting

Image prompting
[
edit
]
In 2023,Meta's AI research released Segment Anything, acomputer visionmodel that can performimage segmentationby prompting. As an alternative to text prompts, Segment Anything can accept bounding boxes, segmentation masks, and foreground/background points.[43]

In 2023,
Meta
's AI research released Segment Anything, a
computer vision
model that can perform
image segmentation
by prompting. As an alternative to text prompts, Segment Anything can accept bounding boxes, segmentation masks, and foreground/background points.
[
43
]

### Limitations

Limitations
[
edit
]
The process of writing and refining a prompt for an LLM or generative AI shares some parallels with an iterative engineering design process, such as by discovering reusable best practices through reproducible experimentation. However, several fundamental limitations constrain its reliability as a discipline. Effective prompting strategies are highly model specific, a technique that improves performance on one model may degrade it on another, making generalization difficult. Prompts are also brittle: minor surface-level changes in phrasing, punctuation, or word order can produce dramatically different outputs, even when the semantic intent remains identical.[44]This instability makes it difficult to establish durable, transferable prompt patterns across deployment contexts.[45]Furthermore, as AI models continue to improve in their ability to interpret user intent directly, many manual prompting techniques are becoming obsolete. Advances in instruction-following and model reasoning have reduced the marginal value of elaborate prompt construction for everyday tasks, raising questions about the long-term viability of prompt engineering as a standalone discipline.[46]

The process of writing and refining a prompt for an LLM or generative AI shares some parallels with an iterative engineering design process, such as by discovering reusable best practices through reproducible experimentation. However, several fundamental limitations constrain its reliability as a discipline. Effective prompting strategies are highly model specific, a technique that improves performance on one model may degrade it on another, making generalization difficult. Prompts are also brittle: minor surface-level changes in phrasing, punctuation, or word order can produce dramatically different outputs, even when the semantic intent remains identical.
[
44
]
This instability makes it difficult to establish durable, transferable prompt patterns across deployment contexts.
[
45
]
Furthermore, as AI models continue to improve in their ability to interpret user intent directly, many manual prompting techniques are becoming obsolete. Advances in instruction-following and model reasoning have reduced the marginal value of elaborate prompt construction for everyday tasks, raising questions about the long-term viability of prompt engineering as a standalone discipline.
[
46
]

## Automated prompt generation

Automated prompt generation
[
edit
]
Recent research has explored automated prompt engineering, using optimization algorithms to generate or refine prompts without human intervention. These automated approaches aim to identify effective prompt patterns by analyzing model gradients, reinforcement feedback, or evolutionary processes, reducing the need for manual experimentation.[47]

Recent research has explored automated prompt engineering, using optimization algorithms to generate or refine prompts without human intervention. These automated approaches aim to identify effective prompt patterns by analyzing model gradients, reinforcement feedback, or evolutionary processes, reducing the need for manual experimentation.
[
47
]

### Retrieval-augmented generation (RAG)

Retrieval-augmented generation (RAG)
[
edit
]
Retrieval-augmented generationis a technique that enables GenAI models to retrieve and incorporate new information. It modifies interactions with an LLM so that the model responds to user queries with reference to a specified set of documents, using this information to supplement information from its pre-existingtraining data. This allows LLMs to use domain-specific and/or updated information.[11]

Retrieval-augmented generation
is a technique that enables GenAI models to retrieve and incorporate new information. It modifies interactions with an LLM so that the model responds to user queries with reference to a specified set of documents, using this information to supplement information from its pre-existing
training data
. This allows LLMs to use domain-specific and/or updated information.
[
11
]
RAG improves large language models by incorporatinginformation retrievalbefore generating responses. Unlike traditional LLMs that rely on static training data, RAG pulls relevant text from databases, uploaded documents, or web sources. By dynamically retrieving information, RAG enables AI to generate more accurate responses and fewerAI hallucinationswithout frequent retraining.[48]

RAG improves large language models by incorporating
information retrieval
before generating responses. Unlike traditional LLMs that rely on static training data, RAG pulls relevant text from databases, uploaded documents, or web sources. By dynamically retrieving information, RAG enables AI to generate more accurate responses and fewer
AI hallucinations
without frequent retraining.
[
48
]

### Graph retrieval-augmented generation (GraphRAG)

Graph retrieval-augmented generation (GraphRAG)
[
edit
]
GraphRAG with a knowledge graph combining access patterns for unstructured, structured, and mixed data
GraphRAG (coined byMicrosoft Research) is a technique that extends RAG with the use of aknowledge graphto allow the model to connect disparate pieces of information, synthesize insights, and understand summarized semantic concepts over large data collections. It was shown to be effective on datasets like the Violent Incident Information from News Articles.[49][50][51]

GraphRAG (coined by
Microsoft Research
) is a technique that extends RAG with the use of a
knowledge graph
to allow the model to connect disparate pieces of information, synthesize insights, and understand summarized semantic concepts over large data collections. It was shown to be effective on datasets like the Violent Incident Information from News Articles.
[
49
]
[
50
]
[
51
]

### Using language models to generate prompts

Using language models to generate prompts
[
edit
]
LLMs themselves can be used to compose prompts for LLMs.[52]Theautomatic prompt engineeralgorithm uses one LLM tobeam searchover prompts for another LLM:[53][54]

LLMs themselves can be used to compose prompts for LLMs.
[
52
]
The
automatic prompt engineer
algorithm uses one LLM to
beam search
over prompts for another LLM:
[
53
]
[
54
]
- There are two LLMs. One is the target LLM, and another is the prompting LLM.
There are two LLMs. One is the target LLM, and another is the prompting LLM.
- Prompting LLM is presented with example input-output pairs, and asked to generate instructions that could have caused a model following the instructions to generate the outputs, given the inputs.
Prompting LLM is presented with example input-output pairs, and asked to generate instructions that could have caused a model following the instructions to generate the outputs, given the inputs.
- Each of the generated instructions is used to prompt the target LLM, followed by each of the inputs. The log-probabilities of the outputs are computed and added. This is the score of the instruction.
Each of the generated instructions is used to prompt the target LLM, followed by each of the inputs. The log-probabilities of the outputs are computed and added. This is the score of the instruction.
- The highest-scored instructions are given to the prompting LLM for further variations.
The highest-scored instructions are given to the prompting LLM for further variations.
- Repeat until some stopping criteria is reached, then output the highest-scored instructions.
Repeat until some stopping criteria is reached, then output the highest-scored instructions.
CoT examples can be generated by LLM themselves. In "auto-CoT", a library of questions are converted to vectors by a model such asBERT. The question vectors areclustered. Questions close to thecentroidof each cluster are selected, in order to have a subset of diverse questions. An LLM does zero-shot CoT on each selected question. The question and the corresponding CoT answer are added to a dataset of demonstrations. These diverse demonstrations can then added to prompts for few-shot learning.[55]

CoT examples can be generated by LLM themselves. In "auto-CoT", a library of questions are converted to vectors by a model such as
BERT
. The question vectors are
clustered
. Questions close to the
centroid
of each cluster are selected, in order to have a subset of diverse questions. An LLM does zero-shot CoT on each selected question. The question and the corresponding CoT answer are added to a dataset of demonstrations. These diverse demonstrations can then added to prompts for few-shot learning.
[
55
]

### Automatic prompt optimization

Automatic prompt optimization
[
edit
]
Automatic prompt optimization techniques refine prompts for large language models by automatically searching over alternative prompt strings using evaluation datasets and task-specific metrics:

Automatic prompt optimization techniques refine prompts for large language models by automatically searching over alternative prompt strings using evaluation datasets and task-specific metrics:
- MIPRO (Multi-prompt Instruction Proposal Optimizer) optimizes the instructions and few-shot demonstrations of multi-stage language model programs, proposing small changes to module prompts and retaining those that improve a downstream performance metric without access to module-level labels or gradients.[56]
MIPRO (Multi-prompt Instruction Proposal Optimizer) optimizes the instructions and few-shot demonstrations of multi-stage language model programs, proposing small changes to module prompts and retaining those that improve a downstream performance metric without access to module-level labels or gradients.
[
56
]
- GEPA (Genetic-Pareto) is a reflective prompt optimizer for compound AI systems that combines language-model-based analysis of execution traces and textual feedback with a Pareto-based evolutionary search over a population of candidate systems; across four tasks, GEPA reports average gains of about 10% overreinforcement-learning-based Group Relative Policy Optimization (GRPO) and over 10% over the MIPROv2 prompt optimizer, while using up to 35 times fewer rollouts than GRPO.[57]
GEPA (Genetic-Pareto) is a reflective prompt optimizer for compound AI systems that combines language-model-based analysis of execution traces and textual feedback with a Pareto-based evolutionary search over a population of candidate systems; across four tasks, GEPA reports average gains of about 10% over
reinforcement-learning
-based Group Relative Policy Optimization (GRPO) and over 10% over the MIPROv2 prompt optimizer, while using up to 35 times fewer rollouts than GRPO.
[
57
]
- Open-source frameworks such as DSPy and Opik expose these and related optimizers, allowing prompt search to be expressed as part of a programmatic pipeline rather than through manual trial and error.[58][59]
Open-source frameworks such as DSPy and Opik expose these and related optimizers, allowing prompt search to be expressed as part of a programmatic pipeline rather than through manual trial and error.
[
58
]
[
59
]

### Using gradient descent to search for prompts

Using gradient descent to search for prompts
[
edit
]
In "prefix-tuning",[60]"prompt tuning", or "soft prompting",[61]floating-pointvectors are searched directly bygradient descentto maximize the log-likelihood on outputs. An earlier result uses the same idea of gradient descent search, but is designed for masked language models like BERT, and searches only over token sequences, rather than numerical vectors. Formally, it searches forarg⁡maxX~∑ilog⁡Pr[Yi|X~∗Xi]{\displaystyle \arg \max _{\tilde {X}}\sum _{i}\log Pr[Y^{i}|{\tilde {X}}\ast X^{i}]}whereX~{\displaystyle {\tilde {X}}}ranges over token sequences of a specified length.[62]

In "prefix-tuning",
[
60
]
"prompt tuning", or "soft prompting",
[
61
]
floating-point
vectors are searched directly by
gradient descent
to maximize the log-likelihood on outputs. An earlier result uses the same idea of gradient descent search, but is designed for masked language models like BERT, and searches only over token sequences, rather than numerical vectors. Formally, it searches for
arg
⁡
⁡
max
X
~
~
∑
∑
i
log
⁡
⁡
P
r
[
Y
i
|
X
~
~
∗
∗
X
i
]
{\displaystyle \arg \max _{\tilde {X}}\sum _{i}\log Pr[Y^{i}|{\tilde {X}}\ast X^{i}]}
where
X
~
~
{\displaystyle {\tilde {X}}}
ranges over token sequences of a specified length.
[
62
]

## History

History
[
edit
]
Early precedents of structured user interaction with ruled-based AI systems can be found in enterprise automation software from 1990s. For example, The Intelligent Filling Manager (1999), developed by Krishna C. Mukherjee, used a dynamic Q&A interface driven by rule-basedexpert systemto collect user inputs for generating regulatory filings automatically across jurisdictions.[63]While not involving neural networks, such systems featured prompt-like workflows that influenced later human-in-the-loop AI designs. In 2018, researchers first proposed that all previously separate tasks innatural language processing(NLP) could be cast as question-answer problems over a context. In addition, they trained a first single, joint, multi-task model that would answer any task-related question like "What is the sentiment" or "Translate this sentence to German" or "Who is the president?"[64]

Early precedents of structured user interaction with ruled-based AI systems can be found in enterprise automation software from 1990s. For example, The Intelligent Filling Manager (1999), developed by Krishna C. Mukherjee, used a dynamic Q&A interface driven by rule-based
expert system
to collect user inputs for generating regulatory filings automatically across jurisdictions.
[
63
]
While not involving neural networks, such systems featured prompt-like workflows that influenced later human-in-the-loop AI designs. In 2018, researchers first proposed that all previously separate tasks in
natural language processing
(NLP) could be cast as question-answer problems over a context. In addition, they trained a first single, joint, multi-task model that would answer any task-related question like "What is the sentiment" or "Translate this sentence to German" or "Who is the president?"
[
64
]
TheAI boomsaw an increased focus within academic literature and professional practice on applying prompting techniques to get the model to output the desired outcome and avoidnonsensical output, a process characterized bytrial-and-error.[65]After the release ofChatGPTin 2022, prompt engineering was soon seen as an important business skill; companies began hiring dedicated prompt engineers, although, given advances in AI's ability to generate prompts better than humans, the employment market for prompt engineers has faced uncertainty.[4]According toThe Wall Street Journalin 2025, the job of prompt engineer was one of the hottest in 2023, but has become obsolete due to models that better intuit user intent and to company trainings.[66]

The
AI boom
saw an increased focus within academic literature and professional practice on applying prompting techniques to get the model to output the desired outcome and avoid
nonsensical output
, a process characterized by
trial-and-error
.
[
65
]
After the release of
ChatGPT
in 2022, prompt engineering was soon seen as an important business skill; companies began hiring dedicated prompt engineers, although, given advances in AI's ability to generate prompts better than humans, the employment market for prompt engineers has faced uncertainty.
[
4
]
According to
The Wall Street Journal
in 2025, the job of prompt engineer was one of the hottest in 2023, but has become obsolete due to models that better intuit user intent and to company trainings.
[
66
]
A repository for prompts reported that over 2,000 public prompts for around 170 datasets were available in February 2022.[67]In 2022, thechain-of-thoughtprompting technique was proposed byGoogleresearchers.[9][68]In 2023, several text-to-text and text-to-image prompt databases were made publicly available.[69][70]The Personalized Image-Prompt (PIP) dataset, a generated image-text dataset that has been categorized by 3,115 users, has also been made available publicly in 2024.[71]

A repository for prompts reported that over 2,000 public prompts for around 170 datasets were available in February 2022.
[
67
]
In 2022, the
chain-of-thought
prompting technique was proposed by
Google
researchers.
[
9
]
[
68
]
In 2023, several text-to-text and text-to-image prompt databases were made publicly available.
[
69
]
[
70
]
The Personalized Image-Prompt (PIP) dataset, a generated image-text dataset that has been categorized by 3,115 users, has also been made available publicly in 2024.
[
71
]

## Prompt injection

Prompt injection
[
edit
]
Main article:
Prompt injection
See also:
SQL injection
,
Cross-site scripting
, and
Social engineering (security)
Prompt injection is acybersecurityexploit in which adversaries craft inputs that appear legitimate but are designed to cause unintended behavior inmachine learning models, particularly large language models. This attack takes advantage of the model's inability to distinguish between developer-defined prompts and user inputs, allowing adversaries to bypass safeguards and influence model behaviour. While LLMs are designed to follow trusted instructions, they can be manipulated into carrying out unintended responses through carefully crafted inputs.[72][73]

Prompt injection is a
cybersecurity
exploit in which adversaries craft inputs that appear legitimate but are designed to cause unintended behavior in
machine learning models
, particularly large language models. This attack takes advantage of the model's inability to distinguish between developer-defined prompts and user inputs, allowing adversaries to bypass safeguards and influence model behaviour. While LLMs are designed to follow trusted instructions, they can be manipulated into carrying out unintended responses through carefully crafted inputs.
[
72
]
[
73
]

## References

References
[
edit
]
- ^"prompt engineering".Oxford English Dictionary.Oxford University Press. 2025.
^
"prompt engineering".
Oxford English Dictionary
.
Oxford University Press
. 2025.
- ^"Oxford Word of the Year 2023".Oxford Languages.Oxford University Press. RetrievedFebruary 6,2026.
^
"Oxford Word of the Year 2023"
.
Oxford Languages
.
Oxford University Press
. Retrieved
February 6,
2026
.
- ^Radford, Alec; Wu, Jeffrey; Child, Rewon; Luan, David;Amodei, Dario;Sutskever, Ilya(2019)."Language Models are Unsupervised Multitask Learners"(PDF). OpenAI.We demonstrate language models can perform down-stream tasks in a zero-shot setting – without any parameter or architecture modification
^
Radford, Alec; Wu, Jeffrey; Child, Rewon; Luan, David;
Amodei, Dario
;
Sutskever, Ilya
(2019).
"Language Models are Unsupervised Multitask Learners"
(PDF)
. OpenAI.
We demonstrate language models can perform down-stream tasks in a zero-shot setting – without any parameter or architecture modification
- ^abGenkina, Dina (March 6, 2024)."AI Prompt Engineering is Dead: Long live AI prompt engineering".IEEE Spectrum. RetrievedJanuary 18,2025.
^
a
b
Genkina, Dina (March 6, 2024).
"AI Prompt Engineering is Dead: Long live AI prompt engineering"
.
IEEE Spectrum
. Retrieved
January 18,
2025
.
- ^abWahle, Jan Philip; Ruas, Terry; Xu, Yang; Gipp, Bela (2024)."Paraphrase Types Elicit Prompt Engineering Capabilities". In Al-Onaizan, Yaser; Bansal, Mohit; Chen, Yun-Nung (eds.).Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing. Miami, Florida, USA: Association for Computational Linguistics. pp.11004–11033.arXiv:2406.19898.doi:10.18653/v1/2024.emnlp-main.617.
^
a
b
Wahle, Jan Philip; Ruas, Terry; Xu, Yang; Gipp, Bela (2024).
"Paraphrase Types Elicit Prompt Engineering Capabilities"
. In Al-Onaizan, Yaser; Bansal, Mohit; Chen, Yun-Nung (eds.).
Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing
. Miami, Florida, USA: Association for Computational Linguistics. pp.
11004–
11033.
arXiv
:
2406.19898
.
doi
:
10.18653/v1/2024.emnlp-main.617
.
- ^Heaven, Will Douglas (April 6, 2022)."This horse-riding astronaut is a milestone on AI's long road towards understanding".MIT Technology Review. RetrievedAugust 14,2023.
^
Heaven, Will Douglas (April 6, 2022).
"This horse-riding astronaut is a milestone on AI's long road towards understanding"
.
MIT Technology Review
. Retrieved
August 14,
2023
.
- ^Wiggers, Kyle (June 12, 2023)."Meta open sources an AI-powered music generator". TechCrunch. RetrievedAugust 15,2023.Next, I gave a more complicated prompt to attempt to throw MusicGen for a loop: "Lo-fi slow BPM electro chill with organic samples."
^
Wiggers, Kyle (June 12, 2023).
"Meta open sources an AI-powered music generator"
. TechCrunch
. Retrieved
August 15,
2023
.
Next, I gave a more complicated prompt to attempt to throw MusicGen for a loop: "Lo-fi slow BPM electro chill with organic samples."
- ^abMittal, Aayush (July 27, 2023)."Mastering AI Art: A Concise Guide to Midjourney and Prompt Engineering".Unite.AI. RetrievedMay 9,2025.
^
a
b
Mittal, Aayush (July 27, 2023).
"Mastering AI Art: A Concise Guide to Midjourney and Prompt Engineering"
.
Unite.AI
. Retrieved
May 9,
2025
.
- ^abcdefWei, Jason; Wang, Xuezhi; Schuurmans, Dale; Bosma, Maarten; Ichter, Brian; Xia, Fei; Chi, Ed H.; Le, Quoc V.; Zhou, Denny (October 31, 2022).Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. Advances in Neural Information Processing Systems (NeurIPS 2022). Vol. 35.arXiv:2201.11903.
^
a
b
c
d
e
f
Wei, Jason; Wang, Xuezhi; Schuurmans, Dale; Bosma, Maarten; Ichter, Brian; Xia, Fei; Chi, Ed H.; Le, Quoc V.; Zhou, Denny (October 31, 2022).
Chain-of-Thought Prompting Elicits Reasoning in Large Language Models
. Advances in Neural Information Processing Systems (NeurIPS 2022). Vol. 35.
arXiv
:
2201.11903
.
- ^abTree of Thoughts: Deliberate Problem Solving with Large Language Models. NeurIPS. 2023.arXiv:2305.10601.
^
a
b
Tree of Thoughts: Deliberate Problem Solving with Large Language Models
. NeurIPS. 2023.
arXiv
:
2305.10601
.
- ^ab"Why Google's AI Overviews gets things wrong".MIT Technology Review. May 31, 2024. RetrievedMarch 7,2025.
^
a
b
"Why Google's AI Overviews gets things wrong"
.
MIT Technology Review
. May 31, 2024
. Retrieved
March 7,
2025
.
- ^abSchulhoff, Sander; et al. (2024). "The Prompt Report: A Systematic Survey of Prompt Engineering Techniques".arXiv:2406.06608[cs.CL].
^
a
b
Schulhoff, Sander; et al. (2024). "The Prompt Report: A Systematic Survey of Prompt Engineering Techniques".
arXiv
:
2406.06608
[
cs.CL
].
- ^Kolirin, Lianne (November 6, 2025)."'Vibe coding' named Collins Dictionary's Word of the Year".CNN. RetrievedFebruary 7,2026.
^
Kolirin, Lianne (November 6, 2025).
"
'Vibe coding' named Collins Dictionary's Word of the Year"
.
CNN
. Retrieved
February 7,
2026
.
- ^Casey, Matt M. (November 5, 2025)."Context Engineering: The Discipline Behind Reliable LLM Applications & Agents". Comet. RetrievedNovember 10,2025.
^
Casey, Matt M. (November 5, 2025).
"Context Engineering: The Discipline Behind Reliable LLM Applications & Agents"
. Comet
. Retrieved
November 10,
2025
.
- ^"Context Engineering". LangChain. July 2, 2025. RetrievedNovember 10,2025.
^
"Context Engineering"
. LangChain. July 2, 2025
. Retrieved
November 10,
2025
.
- ^Mei, Lingrui (July 17, 2025). "A Survey of Context Engineering for Large Language Models".arXiv:2507.13334[cs.CL].
^
Mei, Lingrui (July 17, 2025). "A Survey of Context Engineering for Large Language Models".
arXiv
:
2507.13334
[
cs.CL
].
- ^abWei, Jason; Tay, Yi; Bommasani, Rishi; Raffel, Colin; Zoph, Barret; Borgeaud, Sebastian; Yogatama, Dani; Bosma, Maarten; Zhou, Denny; Metzler, Donald; Chi, Ed H.; Hashimoto, Tatsunori; Vinyals, Oriol; Liang, Percy; Dean, Jeff; Fedus, William (October 2022). "Emergent Abilities of Large Language Models".Transactions on Machine Learning Research.arXiv:2206.07682.In prompting, a pre-trained language model is given a prompt (e.g. a natural language instruction) of a task and completes the response without any further training or gradient updates to its parameters... The ability to perform a task via few-shot prompting is emergent when a model has random performance until a certain scale, after which performance increases to well-above random
^
a
b
Wei, Jason; Tay, Yi; Bommasani, Rishi; Raffel, Colin; Zoph, Barret; Borgeaud, Sebastian; Yogatama, Dani; Bosma, Maarten; Zhou, Denny; Metzler, Donald; Chi, Ed H.; Hashimoto, Tatsunori; Vinyals, Oriol; Liang, Percy; Dean, Jeff; Fedus, William (October 2022). "Emergent Abilities of Large Language Models".
Transactions on Machine Learning Research
.
arXiv
:
2206.07682
.
In prompting, a pre-trained language model is given a prompt (e.g. a natural language instruction) of a task and completes the response without any further training or gradient updates to its parameters... The ability to perform a task via few-shot prompting is emergent when a model has random performance until a certain scale, after which performance increases to well-above random
- ^Caballero, Ethan; Gupta, Kshitij; Rish, Irina; Krueger, David (2023). "Broken Neural Scaling Laws".ICLR.arXiv:2210.14891.
^
Caballero, Ethan; Gupta, Kshitij; Rish, Irina; Krueger, David (2023). "Broken Neural Scaling Laws".
ICLR
.
arXiv
:
2210.14891
.
- ^Musser, George."How AI Knows Things No One Told It".Scientific American. RetrievedMay 17,2023.By the time you type a query into ChatGPT, the network should be fixed; unlike humans, it should not continue to learn. So it came as a surprise that LLMs do, in fact, learn from their users' prompts—an ability known as in-context learning.
^
Musser, George
.
"How AI Knows Things No One Told It"
.
Scientific American
. Retrieved
May 17,
2023
.
By the time you type a query into ChatGPT, the network should be fixed; unlike humans, it should not continue to learn. So it came as a surprise that LLMs do, in fact, learn from their users' prompts—an ability known as in-context learning.
- ^Garg, Shivam; Tsipras, Dimitris; Liang, Percy; Valiant, Gregory (2022). "What Can Transformers Learn In-Context? A Case Study of Simple Function Classes".NeurIPS.arXiv:2208.01066.Training a model to perform in-context learning can be viewed as an instance of the more general learning-to-learn or meta-learning paradigm
^
Garg, Shivam; Tsipras, Dimitris; Liang, Percy; Valiant, Gregory (2022). "What Can Transformers Learn In-Context? A Case Study of Simple Function Classes".
NeurIPS
.
arXiv
:
2208.01066
.
Training a model to perform in-context learning can be viewed as an instance of the more general learning-to-learn or meta-learning paradigm
- ^abQuantifying Language Models' Sensitivity to Spurious Features in Prompt Design or: How I learned to start worrying about prompt formatting. ICLR. 2024.arXiv:2310.11324.
^
a
b
Quantifying Language Models' Sensitivity to Spurious Features in Prompt Design or: How I learned to start worrying about prompt formatting
. ICLR. 2024.
arXiv
:
2310.11324
.
- ^Leidinger, Alina; van Rooij, Robert; Shutova, Ekaterina (2023). Bouamor, Houda; Pino, Juan; Bali, Kalika (eds.)."The language of prompting: What linguistic properties make a prompt successful?".Findings of the Association for Computational Linguistics: EMNLP 2023. Singapore: Association for Computational Linguistics:9210–9232.arXiv:2311.01967.doi:10.18653/v1/2023.findings-emnlp.618.
^
Leidinger, Alina; van Rooij, Robert; Shutova, Ekaterina (2023). Bouamor, Houda; Pino, Juan; Bali, Kalika (eds.).
"The language of prompting: What linguistic properties make a prompt successful?"
.
Findings of the Association for Computational Linguistics: EMNLP 2023
. Singapore: Association for Computational Linguistics:
9210–
9232.
arXiv
:
2311.01967
.
doi
:
10.18653/v1/2023.findings-emnlp.618
.
- ^Linzbach, Stephan; Dimitrov, Dimitar; Kallmeyer, Laura; Evang, Kilian; Jabeen, Hajira; Dietze, Stefan (June 2024)."Dissecting Paraphrases: The Impact of Prompt Syntax and supplementary Information on Knowledge Retrieval from Pretrained Language Models". In Duh, Kevin; Gomez, Helena; Bethard, Steven (eds.).Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers). Mexico City, Mexico: Association for Computational Linguistics. pp.3645–3655.arXiv:2404.01992.doi:10.18653/v1/2024.naacl-long.201.
^
Linzbach, Stephan; Dimitrov, Dimitar; Kallmeyer, Laura; Evang, Kilian; Jabeen, Hajira; Dietze, Stefan (June 2024).
"Dissecting Paraphrases: The Impact of Prompt Syntax and supplementary Information on Knowledge Retrieval from Pretrained Language Models"
. In Duh, Kevin; Gomez, Helena; Bethard, Steven (eds.).
Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)
. Mexico City, Mexico: Association for Computational Linguistics. pp.
3645–
3655.
arXiv
:
2404.01992
.
doi
:
10.18653/v1/2024.naacl-long.201
.
- ^Efficient multi-prompt evaluation of LLMs. NeurIPS. 2024.arXiv:2405.17202.
^
Efficient multi-prompt evaluation of LLMs
. NeurIPS. 2024.
arXiv
:
2405.17202
.
- ^Brown, Tom; Mann, Benjamin; Ryder, Nick; Subbiah, Melanie; Kaplan, Jared D.; Dhariwal, Prafulla; Neelakantan, Arvind (2020). "Language models are few-shot learners".Advances in Neural Information Processing Systems.33:1877–1901.arXiv:2005.14165.
^
Brown, Tom; Mann, Benjamin; Ryder, Nick; Subbiah, Melanie; Kaplan, Jared D.; Dhariwal, Prafulla; Neelakantan, Arvind (2020). "Language models are few-shot learners".
Advances in Neural Information Processing Systems
.
33
:
1877–
1901.
arXiv
:
2005.14165
.
- ^Wang, Yaqing; Yao, Quanming; Kwok, James T.; Ni, Lionel M. (June 12, 2020)."Generalizing from a Few Examples: A Survey on Few-shot Learning".ACM Comput. Surv.53(3): 63:1–63:34.doi:10.1145/3386252.ISSN0360-0300.
^
Wang, Yaqing; Yao, Quanming; Kwok, James T.; Ni, Lionel M. (June 12, 2020).
"Generalizing from a Few Examples: A Survey on Few-shot Learning"
.
ACM Comput. Surv
.
53
(3): 63:1–63:34.
doi
:
10.1145/3386252
.
ISSN
0360-0300
.
- ^Garg, Shivam; Tsipras, Dimitris;Liang, Percy; Valiant, Gregory (2022). "What Can Transformers Learn In-Context? A Case Study of Simple Function Classes".NeurIPS.arXiv:2208.01066.
^
Garg, Shivam; Tsipras, Dimitris;
Liang, Percy
; Valiant, Gregory (2022). "What Can Transformers Learn In-Context? A Case Study of Simple Function Classes".
NeurIPS
.
arXiv
:
2208.01066
.
- ^Narang, Sharan; Chowdhery, Aakanksha (April 4, 2022)."Pathways Language Model (PaLM): Scaling to 540 Billion Parameters for Breakthrough Performance".ai.googleblog.com.
^
Narang, Sharan; Chowdhery, Aakanksha (April 4, 2022).
"Pathways Language Model (PaLM): Scaling to 540 Billion Parameters for Breakthrough Performance"
.
ai.googleblog.com
.
- ^Dang, Ekta (February 8, 2023)."Harnessing the power of GPT-3 in scientific research".VentureBeat. RetrievedMarch 10,2023.
^
Dang, Ekta (February 8, 2023).
"Harnessing the power of GPT-3 in scientific research"
.
VentureBeat
. Retrieved
March 10,
2023
.
- ^Montti, Roger (May 13, 2022)."Google's Chain of Thought Prompting Can Boost Today's Best Algorithms".Search Engine Journal. RetrievedMarch 10,2023.
^
Montti, Roger (May 13, 2022).
"Google's Chain of Thought Prompting Can Boost Today's Best Algorithms"
.
Search Engine Journal
. Retrieved
March 10,
2023
.
- ^"Scaling Instruction-Finetuned Language Models"(PDF).Journal of Machine Learning Research. 2024.
^
"Scaling Instruction-Finetuned Language Models"
(PDF)
.
Journal of Machine Learning Research
. 2024.
- ^Wei, Jason; Tay, Yi (November 29, 2022)."Better Language Models Without Massive Compute".ai.googleblog.com. RetrievedMarch 10,2023.
^
Wei, Jason; Tay, Yi (November 29, 2022).
"Better Language Models Without Massive Compute"
.
ai.googleblog.com
. Retrieved
March 10,
2023
.
- ^Kojima, Takeshi; Shixiang Shane Gu; Reid, Machel; Matsuo, Yutaka; Iwasawa, Yusuke (2022). "Large Language Models are Zero-Shot Reasoners".NeurIPS.arXiv:2205.11916.
^
Kojima, Takeshi; Shixiang Shane Gu; Reid, Machel; Matsuo, Yutaka; Iwasawa, Yusuke (2022). "Large Language Models are Zero-Shot Reasoners".
NeurIPS
.
arXiv
:
2205.11916
.
- ^Self-Consistency Improves Chain of Thought Reasoning in Language Models. ICLR. 2023.arXiv:2203.11171.
^
Self-Consistency Improves Chain of Thought Reasoning in Language Models
. ICLR. 2023.
arXiv
:
2203.11171
.
- ^Mittal, Aayush (May 27, 2024)."Latest Modern Advances in Prompt Engineering: A Comprehensive Guide".Unite.AI. RetrievedMay 8,2025.
^
Mittal, Aayush (May 27, 2024).
"Latest Modern Advances in Prompt Engineering: A Comprehensive Guide"
.
Unite.AI
. Retrieved
May 8,
2025
.
- ^Goldman, Sharon (January 5, 2023)."Two years after DALL-E debut, its inventor is "surprised" by impact".VentureBeat. RetrievedMay 9,2025.
^
Goldman, Sharon (January 5, 2023).
"Two years after DALL-E debut, its inventor is "surprised" by impact"
.
VentureBeat
. Retrieved
May 9,
2025
.
- ^"Prompts".docs.midjourney.com. RetrievedAugust 14,2023.
^
"Prompts"
.
docs.midjourney.com
. Retrieved
August 14,
2023
.
- ^"Stable Diffusion prompt: a definitive guide". May 14, 2023. RetrievedAugust 14,2023.
^
"Stable Diffusion prompt: a definitive guide"
. May 14, 2023
. Retrieved
August 14,
2023
.
- ^Diab, Mohamad; Herrera, Julian; Chernow, Bob (October 28, 2022)."Stable Diffusion Prompt Book"(PDF). RetrievedAugust 7,2023.Prompt engineering is the process of structuring words that can be interpreted and understood by atext-to-imagemodel. Think of it as the language you need to speak in order to tell an AI model what to draw.
^
Diab, Mohamad; Herrera, Julian; Chernow, Bob (October 28, 2022).
"Stable Diffusion Prompt Book"
(PDF)
. Retrieved
August 7,
2023
.
Prompt engineering is the process of structuring words that can be interpreted and understood by a
text-to-image
model. Think of it as the language you need to speak in order to tell an AI model what to draw.
- ^Heikkilä, Melissa (September 16, 2022)."This Artist Is Dominating AI-Generated Art and He's Not Happy About It".MIT Technology Review. RetrievedAugust 14,2023.
^
Heikkilä, Melissa (September 16, 2022).
"This Artist Is Dominating AI-Generated Art and He's Not Happy About It"
.
MIT Technology Review
. Retrieved
August 14,
2023
.
- ^Solomon, Tessa (August 28, 2024)."The AI-Powered Ask Dalí and Hello Vincent Installations Raise Uncomfortable Questions about Ventriloquizing the Dead".ARTnews.com. RetrievedJanuary 10,2025.
^
Solomon, Tessa (August 28, 2024).
"The AI-Powered Ask Dalí and Hello Vincent Installations Raise Uncomfortable Questions about Ventriloquizing the Dead"
.
ARTnews.com
. Retrieved
January 10,
2025
.
- ^Gal, Rinon; Alaluf, Yuval; Atzmon, Yuval; Patashnik, Or; Bermano, Amit H.; Chechik, Gal; Cohen-Or, Daniel (2023). "An Image is Worth One Word: Personalizing Text-to-Image Generation using Textual Inversion".ICLR.arXiv:2208.01618.Using only 3-5 images of a user-provided concept, like an object or a style, we learn to represent it through new "words" in the embedding space of a frozen text-to-image model.
^
Gal, Rinon; Alaluf, Yuval; Atzmon, Yuval; Patashnik, Or; Bermano, Amit H.; Chechik, Gal; Cohen-Or, Daniel (2023). "An Image is Worth One Word: Personalizing Text-to-Image Generation using Textual Inversion".
ICLR
.
arXiv
:
2208.01618
.
Using only 3-5 images of a user-provided concept, like an object or a style, we learn to represent it through new "words" in the embedding space of a frozen text-to-image model.
- ^Segment Anything(PDF). ICCV. 2023.
^
Segment Anything
(PDF)
. ICCV. 2023.
- ^Berry, David M. (June 2, 2026)."Prompt anxiety and the algorithmic politics of uncertainty".AI & SOCIETY.doi:10.1007/s00146-026-03093-8.ISSN1435-5655.
^
Berry, David M. (June 2, 2026).
"Prompt anxiety and the algorithmic politics of uncertainty"
.
AI & SOCIETY
.
doi
:
10.1007/s00146-026-03093-8
.
ISSN
1435-5655
.
- ^Meincke, Lennart; Mollick, Ethan R.; Mollick, Lilach; Shapiro, Dan (March 4, 2025).Prompting Science Report 1: Prompt Engineering is Complicated and Contingent(Report).
^
Meincke, Lennart; Mollick, Ethan R.; Mollick, Lilach; Shapiro, Dan (March 4, 2025).
Prompting Science Report 1: Prompt Engineering is Complicated and Contingent
(Report).
- ^Bousquette, Isabelle (April 25, 2025)."The Hottest AI Job of 2023 Is Already Obsolete".The Wall Street Journal.ISSN0099-9660. RetrievedMay 24,2026.
^
Bousquette, Isabelle (April 25, 2025).
"The Hottest AI Job of 2023 Is Already Obsolete"
.
The Wall Street Journal
.
ISSN
0099-9660
. Retrieved
May 24,
2026
.
- ^Li, Wenwu; Wang, Xiangfeng; Li, Wenhao; Jin, Bo (2025). "A Survey of Automatic Prompt Engineering: An Optimization Perspective".arXiv:2502.11560[cs.AI].
^
Li, Wenwu; Wang, Xiangfeng; Li, Wenhao; Jin, Bo (2025). "A Survey of Automatic Prompt Engineering: An Optimization Perspective".
arXiv
:
2502.11560
[
cs.AI
].
- ^"Can a technology called RAG keep AI models from making stuff up?".Ars Technica. June 6, 2024. RetrievedMarch 7,2025.
^
"Can a technology called RAG keep AI models from making stuff up?"
.
Ars Technica
. June 6, 2024
. Retrieved
March 7,
2025
.
- ^Larson, Jonathan; Truitt, Steven (February 13, 2024),GraphRAG: Unlocking LLM discovery on narrative private data, Microsoft
^
Larson, Jonathan; Truitt, Steven (February 13, 2024),
GraphRAG: Unlocking LLM discovery on narrative private data
, Microsoft
- ^"An Introduction to Graph RAG".KDnuggets. RetrievedMay 9,2025.
^
"An Introduction to Graph RAG"
.
KDnuggets
. Retrieved
May 9,
2025
.
- ^Sequeda, Juan; Allemang, Dean; Jacob, Bryon (2023). "A Benchmark to Understand the Role of Knowledge Graphs on Large Language Model's Accuracy for Question Answering on Enterprise SQL Databases".Grades-Nda.arXiv:2311.07509.
^
Sequeda, Juan; Allemang, Dean; Jacob, Bryon (2023). "A Benchmark to Understand the Role of Knowledge Graphs on Large Language Model's Accuracy for Question Answering on Enterprise SQL Databases".
Grades-Nda
.
arXiv
:
2311.07509
.
- ^Explaining Patterns in Data with Language Models via Interpretable Autoprompting(PDF). BlackboxNLP Workshop. 2023.arXiv:2210.01848.
^
Explaining Patterns in Data with Language Models via Interpretable Autoprompting
(PDF)
. BlackboxNLP Workshop. 2023.
arXiv
:
2210.01848
.
- ^Large Language Models are Human-Level Prompt Engineers. ICLR. 2023.arXiv:2211.01910.
^
Large Language Models are Human-Level Prompt Engineers
. ICLR. 2023.
arXiv
:
2211.01910
.
- ^Pryzant, Reid; Iter, Dan; Li, Jerry; Lee, Yin Tat; Zhu, Chenguang; Zeng, Michael (2023)."Automatic Prompt Optimization with "Gradient Descent" and Beam Search".Conference on Empirical Methods in Natural Language Processing:7957–7968.arXiv:2305.03495.doi:10.18653/v1/2023.emnlp-main.494.
^
Pryzant, Reid; Iter, Dan; Li, Jerry; Lee, Yin Tat; Zhu, Chenguang; Zeng, Michael (2023).
"Automatic Prompt Optimization with "Gradient Descent" and Beam Search"
.
Conference on Empirical Methods in Natural Language Processing
:
7957–
7968.
arXiv
:
2305.03495
.
doi
:
10.18653/v1/2023.emnlp-main.494
.
- ^Automatic Chain of Thought Prompting in Large Language Models. ICLR. 2023.arXiv:2210.03493.
^
Automatic Chain of Thought Prompting in Large Language Models
. ICLR. 2023.
arXiv
:
2210.03493
.
- ^Opsahl-Ong, Krista; Ryan, Michael J.; Purtell, Josh; Broman, David; Potts, Christopher; Zaharia, Matei; Khattab, Omar (2024).Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs. Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing (EMNLP). Miami, Florida: Association for Computational Linguistics.arXiv:2406.11695.doi:10.18653/v1/2024.emnlp-main.525.
^
Opsahl-Ong, Krista; Ryan, Michael J.; Purtell, Josh; Broman, David; Potts, Christopher; Zaharia, Matei; Khattab, Omar (2024).
Optimizing Instructions and Demonstrations for Multi-Stage Language Model Programs
. Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing (EMNLP). Miami, Florida: Association for Computational Linguistics.
arXiv
:
2406.11695
.
doi
:
10.18653/v1/2024.emnlp-main.525
.
- ^Agrawal, Lakshya A. (2025). "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning".arXiv:2507.19457[cs.CL].
^
Agrawal, Lakshya A. (2025). "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning".
arXiv
:
2507.19457
[
cs.CL
].
- ^Khattab, Omar (2023). "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines".arXiv:2310.03714[cs.CL].
^
Khattab, Omar (2023). "DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines".
arXiv
:
2310.03714
[
cs.CL
].
- ^"Agent Optimization".comet.com. RetrievedNovember 29,2025.
^
"Agent Optimization"
.
comet.com
. Retrieved
November 29,
2025
.
- ^Li, Xiang Lisa; Liang, Percy (2021). "Prefix-Tuning: Optimizing Continuous Prompts for Generation".Proceedings of the 59th Annual Meeting of the Association for Computational Linguistics and the 11th International Joint Conference on Natural Language Processing (Volume 1: Long Papers). pp.4582–4597.doi:10.18653/V1/2021.ACL-LONG.353.S2CID230433941.In this paper, we propose prefix-tuning, a lightweight alternative to fine-tuning... Prefix-tuning draws inspiration from prompting
^
Li, Xiang Lisa; Liang, Percy (2021). "Prefix-Tuning: Optimizing Continuous Prompts for Generation".
Proceedings of the 59th Annual Meeting of the Association for Computational Linguistics and the 11th International Joint Conference on Natural Language Processing (Volume 1: Long Papers)
. pp.
4582–
4597.
doi
:
10.18653/V1/2021.ACL-LONG.353
.
S2CID
230433941
.
In this paper, we propose prefix-tuning, a lightweight alternative to fine-tuning... Prefix-tuning draws inspiration from prompting
- ^Lester, Brian; Al-Rfou, Rami; Constant, Noah (2021). "The Power of Scale for Parameter-Efficient Prompt Tuning".Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing. pp.3045–3059.arXiv:2104.08691.doi:10.18653/V1/2021.EMNLP-MAIN.243.S2CID233296808.In this work, we explore "prompt tuning," a simple yet effective mechanism for learning "soft prompts"...Unlike the discrete text prompts used by GPT-3, soft prompts are learned through back-propagation
^
Lester, Brian; Al-Rfou, Rami; Constant, Noah (2021). "The Power of Scale for Parameter-Efficient Prompt Tuning".
Proceedings of the 2021 Conference on Empirical Methods in Natural Language Processing
. pp.
3045–
3059.
arXiv
:
2104.08691
.
doi
:
10.18653/V1/2021.EMNLP-MAIN.243
.
S2CID
233296808
.
In this work, we explore "prompt tuning," a simple yet effective mechanism for learning "soft prompts"...Unlike the discrete text prompts used by GPT-3, soft prompts are learned through back-propagation
- ^Shin, Taylor; Razeghi, Yasaman; Logan IV, Robert L.; Wallace, Eric; Singh, Sameer (November 2020)."AutoPrompt: Eliciting Knowledge from Language Models with Automatically Generated Prompts".Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP). Online: Association for Computational Linguistics. pp.4222–4235.doi:10.18653/v1/2020.emnlp-main.346.S2CID226222232.
^
Shin, Taylor; Razeghi, Yasaman; Logan IV, Robert L.; Wallace, Eric; Singh, Sameer (November 2020).
"AutoPrompt: Eliciting Knowledge from Language Models with Automatically Generated Prompts"
.
Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)
. Online: Association for Computational Linguistics. pp.
4222–
4235.
doi
:
10.18653/v1/2020.emnlp-main.346
.
S2CID
226222232
.
- ^Mukherjee, Krishna C. (1999).Automating Forms Publishing with the Intelligent Filing Manager. IEEE International Conference on Systems, Man, and Cybernetics. pp.378–383.doi:10.1109/ICSMC.1999.814108.
^
Mukherjee, Krishna C. (1999).
Automating Forms Publishing with the Intelligent Filing Manager
. IEEE International Conference on Systems, Man, and Cybernetics. pp.
378–
383.
doi
:
10.1109/ICSMC.1999.814108
.
- ^McCann, Bryan; Keskar, Nitish; Xiong, Caiming; Socher, Richard (June 20, 2018).The Natural Language Decathlon: Multitask Learning as Question Answering. ICLR.arXiv:1806.08730.
^
McCann, Bryan; Keskar, Nitish; Xiong, Caiming; Socher, Richard (June 20, 2018).
The Natural Language Decathlon: Multitask Learning as Question Answering
. ICLR.
arXiv
:
1806.08730
.
- ^Knoth, Nils; Tolzin, Antonia; Janson, Andreas; Leimeister, Jan Marco (June 1, 2024)."AI literacy and its implications for prompt engineering strategies".Computers and Education: Artificial Intelligence.6100225.doi:10.1016/j.caeai.2024.100225.ISSN2666-920X.
^
Knoth, Nils; Tolzin, Antonia; Janson, Andreas; Leimeister, Jan Marco (June 1, 2024).
"AI literacy and its implications for prompt engineering strategies"
.
Computers and Education: Artificial Intelligence
.
6
100225.
doi
:
10.1016/j.caeai.2024.100225
.
ISSN
2666-920X
.
- ^Bousquette, Isabelle (April 25, 2025)."The Hottest AI Job of 2023 Is Already Obsolete".Wall Street Journal.ISSN0099-9660. RetrievedMay 7,2025.
^
Bousquette, Isabelle (April 25, 2025).
"The Hottest AI Job of 2023 Is Already Obsolete"
.
Wall Street Journal
.
ISSN
0099-9660
. Retrieved
May 7,
2025
.
- ^PromptSource: An Integrated Development Environment and Repository for Natural Language Prompts. Association for Computational Linguistics. 2022.
^
PromptSource: An Integrated Development Environment and Repository for Natural Language Prompts
. Association for Computational Linguistics. 2022.
- ^Brubaker, Ben (March 21, 2024)."How Chain-of-Thought Reasoning Helps Neural Networks Compute".Quanta Magazine. RetrievedMay 9,2025.
^
Brubaker, Ben (March 21, 2024).
"How Chain-of-Thought Reasoning Helps Neural Networks Compute"
.
Quanta Magazine
. Retrieved
May 9,
2025
.
- ^Chen, Brian X. (June 23, 2023)."How to Turn Your Chatbot Into a Life Coach".The New York Times.
^
Chen, Brian X. (June 23, 2023).
"How to Turn Your Chatbot Into a Life Coach"
.
The New York Times
.
- ^Chen, Brian X. (May 25, 2023)."Get the Best From ChatGPT With These Golden Prompts".The New York Times.ISSN0362-4331. RetrievedAugust 16,2023.
^
Chen, Brian X. (May 25, 2023).
"Get the Best From ChatGPT With These Golden Prompts"
.
The New York Times
.
ISSN
0362-4331
. Retrieved
August 16,
2023
.
- ^Chen, Zijie; Zhang, Lichao; Weng, Fangsheng; Pan, Lili; Lan, Zhenzhong (June 16, 2024)."Tailored Visions: Enhancing Text-to-Image Generation with Personalized Prompt Rewriting".2024 IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR). IEEE. pp.7727–7736.arXiv:2310.08129.doi:10.1109/cvpr52733.2024.00738.ISBN979-8-3503-5300-6.
^
Chen, Zijie; Zhang, Lichao; Weng, Fangsheng; Pan, Lili; Lan, Zhenzhong (June 16, 2024).
"Tailored Visions: Enhancing Text-to-Image Generation with Personalized Prompt Rewriting"
.
2024 IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)
. IEEE. pp.
7727–
7736.
arXiv
:
2310.08129
.
doi
:
10.1109/cvpr52733.2024.00738
.
ISBN
979-8-3503-5300-6
.
- ^Vigliarolo, Brandon (September 19, 2022)."GPT-3 'prompt injection' attack causes bot bad manners".The Register. RetrievedFebruary 9,2023.
^
Vigliarolo, Brandon (September 19, 2022).
"GPT-3 'prompt injection' attack causes bot bad manners"
.
The Register
. Retrieved
February 9,
2023
.
- ^"What is a prompt injection attack?".IBM. March 26, 2024. RetrievedMarch 7,2025.
^
"What is a prompt injection attack?"
.
IBM
. March 26, 2024
. Retrieved
March 7,
2025
.
Scholia
has a
topic
profile for
Prompt engineering
.

<!-- table omitted -->

- v
v
- t
t
- e
e
Generative AI
Concepts
- Autoencoder
Autoencoder
- Deep learning
Deep learning
- Fine-tuning
Fine-tuning
- Foundation model
Foundation model
- Generative adversarial network
Generative adversarial network
- Generative pre-trained transformer
Generative pre-trained transformer
- Large language model
Large language model
- Model Context Protocol
Model Context Protocol
- Neural network
Neural network
- Prompt engineering
Prompt engineering
- Reinforcement learning from human feedback
Reinforcement learning from human feedback
- Retrieval-augmented generation
Retrieval-augmented generation
- Self-supervised learning
Self-supervised learning
- Stochastic parrot
Stochastic parrot
- Synthetic data
Synthetic data
- Top-p sampling
Top-p sampling
- Transformer
Transformer
- Variational autoencoder
Variational autoencoder
- Vibe coding
Vibe coding
- Vision transformer
Vision transformer
- Word embedding
Word embedding
Models

<!-- table omitted -->

Text
- Amazon Nova
Amazon Nova
- Character.ai
Character.ai
- Claude
Claude
- Command
Command
- DeepSeek
DeepSeek
- Doubao
Doubao
- Ernie
Ernie
- EXAONE
EXAONE
- Gemini
Gemini
- Gemma
Gemma
- GLM
GLM
- GPTChatGPT
GPT
- ChatGPT
ChatGPT
- Grok
Grok
- IBM Granite
IBM Granite
- Kimi
Kimi
- MAI
MAI
- Microsoft Copilot
Microsoft Copilot
- Mistral
Mistral
- MiniMax
MiniMax
- Muse Spark
Muse Spark
- Nemotron
Nemotron
- Perplexity
Perplexity
- Solar
Solar
- Poe
Poe
- HKChat
HKChat
- Qwen
Qwen
- Tencent Hy
Tencent Hy
- Xiaomi MiMo
Xiaomi MiMo
- You.com
You.com
Image
- Adobe Firefly
Adobe Firefly
- Flux
Flux
- GPT Image
GPT Image
- Ideogram
Ideogram
- Midjourney
Midjourney
- Nano Banana
Nano Banana
- Recraft
Recraft
- Seedream
Seedream
- Stable Diffusion
Stable Diffusion
Video
- Dream Machine
Dream Machine
- Genieworld model
Genie
- world model
world model
- Hailuo AI
Hailuo AI
- Kling AI
Kling AI
- LTX
LTX
- Runway Gen
Runway Gen
- Seedance
Seedance
- Sora
Sora
- Veo
Veo
Speech
- 15.ai
15.ai
- Eleven
Eleven
- Gemini Speech
Gemini Speech
- MiniMax Speech
MiniMax Speech
Music
- Eleven Music
Eleven Music
- Endel
Endel
- MiniMax Music
MiniMax Music
- Riffusion
Riffusion
- Suno
Suno
- Udio
Udio
Products

<!-- table omitted -->

Coding tools
- Claude Code
Claude Code
- Codex
Codex
- Cursor
Cursor
- Devin AI
Devin AI
- GitHub Copilot
GitHub Copilot
- Google Antigravity
Google Antigravity
- Replit
Replit
Agents
- AutoGPT
AutoGPT
- ChatGPT agent
ChatGPT agent
- Claude Cowork
Claude Cowork
- Gemini Spark
Gemini Spark
- Manus
Manus
- MiniMax Agent
MiniMax Agent
- OpenClaw
OpenClaw
Applications
- Deepfakeaudio
Deepfake
- audio
audio
- Slopslopaganda
Slop
- slopaganda
slopaganda
Companies
- Aleph Alpha
Aleph Alpha
- Anthropic
Anthropic
- Anysphere
Anysphere
- Baichuan
Baichuan
- Canva
Canva
- Cognition AI
Cognition AI
- Cohere
Cohere
- Contextual AI
Contextual AI
- DeepSeek
DeepSeek
- DeepL
DeepL
- EleutherAI
EleutherAI
- ElevenLabs
ElevenLabs
- GoogleAIDeepMind
Google
- AI
AI
- DeepMind
DeepMind
- HeyGen
HeyGen
- Hugging Face
Hugging Face
- Inflection AI
Inflection AI
- Kuaishou
Kuaishou
- Lightricks
Lightricks
- Lovable
Lovable
- Luma Labs
Luma Labs
- Meta AI
Meta AI
- Meta Superintelligence Labs
Meta Superintelligence Labs
- Microsoft AI
Microsoft AI
- MiniMax
MiniMax
- Mistral AI
Mistral AI
- Moonshot AI
Moonshot AI
- OpenAI
OpenAI
- Perplexity AI
Perplexity AI
- Runway
Runway
- Safe Superintelligence
Safe Superintelligence
- Sakana AI
Sakana AI
- Salesforce
Salesforce
- Scale AI
Scale AI
- SoundHound AI
SoundHound AI
- SpaceXAI
SpaceXAI
- Stability AI
Stability AI
- StepFun
StepFun
- Synthesia
Synthesia
- Thinking Machines Lab
Thinking Machines Lab
- Upstage
Upstage
- Xiaomi
Xiaomi
- Z.ai
Z.ai
Controversies
- Generative AI pornographyDeepfake pornographyon Grokof Taylor Swift
Generative AI pornography
- Deepfake pornographyon Grokof Taylor Swift
Deepfake pornography
- on Grok
on Grok
- of Taylor Swift
of Taylor Swift
- Pause Giant AI Experiments
Pause Giant AI Experiments
- Removal of Sam Altman from OpenAI
Removal of Sam Altman from OpenAI
- Statement on AI Risk
Statement on AI Risk
- Tay (chatbot)
Tay (chatbot)
- Théâtre D'opéra Spatial
Théâtre D'opéra Spatial
- Voiceverse NFT plagiarism
Voiceverse NFT plagiarism
- Category
Category
- Commons
Commons

<!-- table omitted -->

- v
v
- t
t
- e
e
Artificial intelligence
(AI)
- Historytimeline
History
- timeline
timeline
- Glossary
Glossary
- Companies
Companies
- Projects
Projects
- List of open-source AI software
List of open-source AI software
Concepts
- Automated reasoning
Automated reasoning
- ParameterHyperparameter
Parameter
- Hyperparameter
Hyperparameter
- Loss functions
Loss functions
- RegressionBias–variance tradeoffDouble descentOverfitting
Regression
- Bias–variance tradeoff
Bias–variance tradeoff
- Double descent
Double descent
- Overfitting
Overfitting
- Clustering
Clustering
- Gradient descentSGDQuasi-Newton methodConjugate gradient method
Gradient descent
- SGD
SGD
- Quasi-Newton method
Quasi-Newton method
- Conjugate gradient method
Conjugate gradient method
- Backpropagation
Backpropagation
- Attention
Attention
- Convolution
Convolution
- NormalizationBatchnorm
Normalization
- Batchnorm
Batchnorm
- ActivationSoftmaxSigmoidRectifier
Activation
- Softmax
Softmax
- Sigmoid
Sigmoid
- Rectifier
Rectifier
- Gating
Gating
- Weight initialization
Weight initialization
- Regularization
Regularization
- DatasetsAugmentation
Datasets
- Augmentation
Augmentation
- Prompt engineering
Prompt engineering
- Reinforcement learningQ-learningSARSAImitationPolicy gradient
Reinforcement learning
- Q-learning
Q-learning
- SARSA
SARSA
- Imitation
Imitation
- Policy gradient
Policy gradient
- Diffusion
Diffusion
- Latent diffusion model
Latent diffusion model
- Autoregression
Autoregression
- Adversary
Adversary
- RAG
RAG
- Uncanny valley
Uncanny valley
- RLHF
RLHF
- Self-supervised learning
Self-supervised learning
- Reflection
Reflection
- Recursive self-improvement
Recursive self-improvement
- Hallucination
Hallucination
- Word embedding
Word embedding
- Vibe coding
Vibe coding
- Symbolic AI
Symbolic AI
- Neuro-symbolic AI
Neuro-symbolic AI
Applications
- Automated theorem proving
Automated theorem proving
- Machine learningIn-context learning
Machine learning
- In-context learning
In-context learning
- Artificial neural networkDeep learning
Artificial neural network
- Deep learning
Deep learning
- Language modelLargeNMTReasoning
Language model
- Large
Large
- NMT
NMT
- Reasoning
Reasoning
- Model Context Protocol
Model Context Protocol
- Intelligent agentAI agent
Intelligent agent
- AI agent
AI agent
- Artificial human companion
Artificial human companion
- Humanity's Last Exam
Humanity's Last Exam
- Lethal autonomous weapons (LAWs)
Lethal autonomous weapons (LAWs)
- Generative AI
Generative AI
- Weak AI
Weak AI
- HypotheticalArtificial general intelligence (AGI)Artificial superintelligence (ASI)
Hypothetical
- Artificial general intelligence (AGI)
Artificial general intelligence (AGI)
- Artificial superintelligence (ASI)
Artificial superintelligence (ASI)
- Agent2Agent protocol
Agent2Agent protocol
Implementations

<!-- table omitted -->

Audio–visual
- AlexNet
AlexNet
- WaveNet
WaveNet
- Human image synthesis
Human image synthesis
- HWR
HWR
- OCR
OCR
- Computer vision
Computer vision
- Speech synthesis15.aiElevenLabs
Speech synthesis
- 15.ai
15.ai
- ElevenLabs
ElevenLabs
- Speech recognitionWhisper
Speech recognition
- Whisper
Whisper
- Facial recognition
Facial recognition
- AlphaFold
AlphaFold
- Text-to-image modelsAuroraDALL-EFireflyFluxGPT ImageIdeogramImagenMidjourneyRecraftStable Diffusion
Text-to-image models
- Aurora
Aurora
- DALL-E
DALL-E
- Firefly
Firefly
- Flux
Flux
- GPT Image
GPT Image
- Ideogram
Ideogram
- Imagen
Imagen
- Midjourney
Midjourney
- Recraft
Recraft
- Stable Diffusion
Stable Diffusion
- Text-to-video modelsDream MachineRunway GenHailuo AIKlingSoraSeedanceVeo
Text-to-video models
- Dream Machine
Dream Machine
- Runway Gen
Runway Gen
- Hailuo AI
Hailuo AI
- Kling
Kling
- Sora
Sora
- Seedance
Seedance
- Veo
Veo
- Music generationRiffusionSunoUdio
Music generation
- Riffusion
Riffusion
- Suno
Suno
- Udio
Udio
- World modelsGenieOasis
World models
- Genie
Genie
- Oasis
Oasis
Text
- List of large language models
List of large language models
- Project Debater
Project Debater
- IBM WatsonIBM Watsonx
IBM Watson
- IBM Watsonx
IBM Watsonx
Decisional
- AlphaGo
AlphaGo
- AlphaZero
AlphaZero
- OpenAI Five
OpenAI Five
- Self-driving car
Self-driving car
- MuZero
MuZero
- Action selectionAutoGPT
Action selection
- AutoGPT
AutoGPT
- Robot control
Robot control
Reasoning systems
- Deductive classifiers
Deductive classifiers
- Expert systems
Expert systems
- Inference engines
Inference engines
- Knowledge-based systems
Knowledge-based systems
- Logic programs
Logic programs
- Procedural reasoning systems
Procedural reasoning systems
- Semantic reasoners
Semantic reasoners
- Rule-based systems
Rule-based systems
Cognitive architectures
- ACT-R
ACT-R
- Soar
Soar
- CLARION
CLARION
- LIDA
LIDA
- OpenCog
OpenCog
Knowledge bases
- ConceptNet
ConceptNet
- Wikidata
Wikidata
- DBpedia
DBpedia
- YAGO
YAGO
People
- Alan Turing
Alan Turing
- Warren Sturgis McCulloch
Warren Sturgis McCulloch
- Walter Pitts
Walter Pitts
- John von Neumann
John von Neumann
- Christopher D. Manning
Christopher D. Manning
- Claude Shannon
Claude Shannon
- Shun'ichi Amari
Shun'ichi Amari
- Kunihiko Fukushima
Kunihiko Fukushima
- Takeo Kanade
Takeo Kanade
- Marvin Minsky
Marvin Minsky
- John McCarthy
John McCarthy
- Nathaniel Rochester
Nathaniel Rochester
- Allen Newell
Allen Newell
- Cliff Shaw
Cliff Shaw
- Herbert A. Simon
Herbert A. Simon
- Oliver Selfridge
Oliver Selfridge
- Frank Rosenblatt
Frank Rosenblatt
- Bernard Widrow
Bernard Widrow
- Joseph Weizenbaum
Joseph Weizenbaum
- Seymour Papert
Seymour Papert
- Seppo Linnainmaa
Seppo Linnainmaa
- Paul Werbos
Paul Werbos
- Geoffrey Hinton
Geoffrey Hinton
- John Hopfield
John Hopfield
- Jürgen Schmidhuber
Jürgen Schmidhuber
- Yann LeCun
Yann LeCun
- Yoshua Bengio
Yoshua Bengio
- Lotfi A. Zadeh
Lotfi A. Zadeh
- Stephen Grossberg
Stephen Grossberg
- Alex Graves
Alex Graves
- James Goodnight
James Goodnight
- Andrew Ng
Andrew Ng
- Fei-Fei Li
Fei-Fei Li
- Alex Krizhevsky
Alex Krizhevsky
- Ilya Sutskever
Ilya Sutskever
- Oriol Vinyals
Oriol Vinyals
- Quoc V. Le
Quoc V. Le
- Ian Goodfellow
Ian Goodfellow
- Demis Hassabis
Demis Hassabis
- David Silver
David Silver
- Andrej Karpathy
Andrej Karpathy
- Ashish Vaswani
Ashish Vaswani
- Noam Shazeer
Noam Shazeer
- Aidan Gomez
Aidan Gomez
- John Schulman
John Schulman
- Mustafa Suleyman
Mustafa Suleyman
- Jan Leike
Jan Leike
- Daniel Kokotajlo
Daniel Kokotajlo
- François Chollet
François Chollet
Neural network architectures
- Neural Turing machine
Neural Turing machine
- Differentiable neural computer
Differentiable neural computer
- TransformerVision transformer (ViT)
Transformer
- Vision transformer (ViT)
Vision transformer (ViT)
- Recurrent neural network (RNN)
Recurrent neural network (RNN)
- Long short-term memory (LSTM)
Long short-term memory (LSTM)
- Gated recurrent unit (GRU)
Gated recurrent unit (GRU)
- Echo state network
Echo state network
- Multilayer perceptron (MLP)
Multilayer perceptron (MLP)
- Convolutional neural network (CNN)
Convolutional neural network (CNN)
- Residual neural network (RNN)
Residual neural network (RNN)
- Highway network
Highway network
- Mamba
Mamba
- Autoencoder
Autoencoder
- Variational autoencoder (VAE)
Variational autoencoder (VAE)
- Generative adversarial network (GAN)
Generative adversarial network (GAN)
- Graph neural network (GNN)
Graph neural network (GNN)
Political
- AI Cold War
AI Cold War
- AI safety(Alignment)
AI safety
(
Alignment
)
- AI takeover
AI takeover
- Elections
Elections
- Ethics of AI
Ethics of AI
- EUAI Act
EU
AI Act
- Nationalism
Nationalism
- Precautionary principle
Precautionary principle
- Regulation of AIUS
Regulation of AI
- US
US
- Virtual politician
Virtual politician
- Propaganda
Propaganda
Social and economic
- AI boom
AI boom
- AI bubble
AI bubble
- AI data center
AI data center
- AI effect
AI effect
- AI literacy
AI literacy
- AI slop
AI slop
- AI veganism
AI veganism
- AI winter
AI winter
- Anthropomorphism
Anthropomorphism
- Arms race
Arms race
- Competition
Competition
- Environmental impact
Environmental impact
- Explainable AI
Explainable AI
- Generative engine optimization
Generative engine optimization
- In architecture
In architecture
- In education
In education
- In fiction
In fiction
- In healthcareChatbot psychosis
In healthcare
- Chatbot psychosis
Chatbot psychosis
- In marketing
In marketing
- In video games
In video games
- In visual art
In visual art
- Military applicationsAI warfare
Military applications
- AI warfare
AI warfare
- Workplace impact
Workplace impact
- Category
Category

<!-- table omitted -->

- v
v
- t
t
- e
e
Natural language processing
General terms
- AI-complete
AI-complete
- Bag-of-words
Bag-of-words
- n-gramBigramTrigram
n
-gram
- Bigram
Bigram
- Trigram
Trigram
- Computational linguistics
Computational linguistics
- Natural language understanding
Natural language understanding
- Stop words
Stop words
- Text processing
Text processing
Text analysis
- Argument mining
Argument mining
- Collocation extraction
Collocation extraction
- Concept mining
Concept mining
- Coreference resolution
Coreference resolution
- Deep linguistic processing
Deep linguistic processing
- Distant reading
Distant reading
- Information extraction
Information extraction
- Knowledge extraction
Knowledge extraction
- Logic translation
Logic translation
- Named-entity recognition
Named-entity recognition
- Ontology learning
Ontology learning
- Parsingsemanticsyntactic
Parsing
- semantic
semantic
- syntactic
syntactic
- Part-of-speech tagging
Part-of-speech tagging
- Semantic analysis
Semantic analysis
- Semantic role labeling
Semantic role labeling
- Semantic decomposition
Semantic decomposition
- Semantic similarity
Semantic similarity
- Sentiment analysis
Sentiment analysis
- Stance detection
Stance detection
- Stylometryadversarial
Stylometry
- adversarial
adversarial
- Terminology extraction
Terminology extraction
- Text mining
Text mining
- Textual entailment
Textual entailment
- Truecasing
Truecasing
- Word-sense disambiguation
Word-sense disambiguation
- Word-sense induction
Word-sense induction

<!-- table omitted -->

Text segmentation
- Compound-term processing
Compound-term processing
- Lemmatization
Lemmatization
- Lexical analysis
Lexical analysis
- Text chunking
Text chunking
- Stemming
Stemming
- Sentence segmentation
Sentence segmentation
- Word segmentation
Word segmentation
Automatic summarization
- Multi-document summarization
Multi-document summarization
- Sentence extraction
Sentence extraction
- Text simplification
Text simplification
Machine translation
- Computer-assisted
Computer-assisted
- Example-based
Example-based
- Rule-based
Rule-based
- Statistical
Statistical
- Transfer-based
Transfer-based
- Neural
Neural
Distributional semantics
models
- BERT
BERT
- Document-term matrix
Document-term matrix
- Explicit semantic analysis
Explicit semantic analysis
- fastText
fastText
- GloVe
GloVe
- Language modellargesmall
Language model
- large
large
- small
small
- Latent semantic analysis
Latent semantic analysis
- Long short-term memory
Long short-term memory
- Seq2seq
Seq2seq
- Transformer
Transformer
- Word embedding
Word embedding
- Word2vec
Word2vec
Language resources
,
datasets and corpora

<!-- table omitted -->

Types and
standards
- Corpus linguistics
Corpus linguistics
- Lexical resource
Lexical resource
- Linguistic Linked Open Data
Linguistic Linked Open Data
- Machine-readable dictionary
Machine-readable dictionary
- Parallel text
Parallel text
- PropBank
PropBank
- Semantic network
Semantic network
- Simple Knowledge Organization System
Simple Knowledge Organization System
- Speech corpus
Speech corpus
- Text corpus
Text corpus
- Thesaurus (information retrieval)
Thesaurus (information retrieval)
- Treebank
Treebank
- Universal Dependencies
Universal Dependencies
Data
- BabelNet
BabelNet
- Bank of English
Bank of English
- DBpedia
DBpedia
- FrameNet
FrameNet
- Google Ngram Viewer
Google Ngram Viewer
- UBY
UBY
- WordNet
WordNet
- Wikidata
Wikidata
Automatic identification
and data capture
- Speech recognition
Speech recognition
- Speech segmentation
Speech segmentation
- Speech synthesis
Speech synthesis
- Natural language generation
Natural language generation
Topic model
- Document classification
Document classification
- Dynamic topic model
Dynamic topic model
- Latent Dirichlet allocation
Latent Dirichlet allocation
- Pachinko allocation
Pachinko allocation
Computer-assisted
reviewing
- Automated essay scoring
Automated essay scoring
- Concordancer
Concordancer
- Grammar checker
Grammar checker
- Predictive text
Predictive text
- Pronunciation assessment
Pronunciation assessment
- Spell checker
Spell checker
Natural language
user interface
- Chatbot
Chatbot
- Interactive fiction
Interactive fiction
- Prompt engineering
Prompt engineering
- Question answering
Question answering
- Virtual assistant
Virtual assistant
- Voice user interface
Voice user interface
Visual-linguistic
- Automatic image annotation
Automatic image annotation
- CLIP
CLIP
- Multimodal sentiment analysis
Multimodal sentiment analysis
- Optical character recognition
Optical character recognition
- Vision-language model
Vision-language model
- Vision–language–action model
Vision–language–action model
Related
- Formal semantics
Formal semantics
- Gensim
Gensim
- Hallucination
Hallucination
- Natural Language Toolkit
Natural Language Toolkit
- spaCy
spaCy
NewPP limit report
Parsed by mw‐web.codfw.main‐8b57965b8‐gjkh9
Cached time: 20260629171259
Cache expiry: 2592000
Cache expiry source: Module:Citation/CS1 (os.date(%Y))
Reduced expiry: false
Complications: [vary‐revision‐sha1, prevent‐selective‐update, show‐toc]
CPU time usage: 0.759 seconds
Real time usage: 0.916 seconds
Preprocessor visited node count: 3887/1000000
Revision size: 47507/2097152 bytes
Post‐expand include size: 255740/2097152 bytes
Template argument size: 1437/2097152 bytes
Highest expansion depth: 12/100
Expensive parser function count: 11/500
Unstrip recursion depth: 1/20
Unstrip post‐expand size: 295222/5000000 bytes
Lua time usage: 0.470/10.000 seconds
Lua memory usage: 6004948/52428800 bytes
Number of Wikibase entities loaded: 0/500
Transclusion expansion time report (%,ms,calls,template)
100.00%  688.631      1 -total
 14.77%  101.698      7 Template:Cite_book
 14.35%   98.822     29 Template:Cite_web
 13.98%   96.236      8 Template:Navbox
 10.88%   74.912      1 Template:Generative_AI
 10.51%   72.357     14 Template:Cite_journal
  7.64%   52.597      1 Template:Short_description
  7.49%   51.611     13 Template:Cite_conference
  4.71%   32.405      2 Template:Pagetype
  4.36%   30.001      5 Template:Cite_arXiv
Render ID c711f07e-73dd-11f1-bf82-51066f3d6259
Saved in parser cache with key enwiki:pcache:69071767:|#|:idhash:canonical and timestamp 20260629171259 and revision id 1360274188. Rendering was triggered because: page_view
Retrieved from "
https://en.wikipedia.org/w/index.php?title=Prompt_engineering&oldid=1360274188
"
Categories
:
- Deep learning
Deep learning
- Machine learning
Machine learning
- Natural language processing
Natural language processing
- Unsupervised learning
Unsupervised learning
- 2022 neologisms
2022 neologisms
- Linguistics
Linguistics
- Generative AI
Generative AI
Hidden categories:
- Articles with short description
Articles with short description
- Short description is different from Wikidata
Short description is different from Wikidata
- Use mdy dates from January 2025
Use mdy dates from January 2025
- Pages using multiple image with auto scaled images
Pages using multiple image with auto scaled images