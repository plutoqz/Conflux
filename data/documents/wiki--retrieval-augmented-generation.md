<!-- source: https://en.wikipedia.org/wiki/Retrieval-augmented_generation -->
# Retrieval-augmented generation

> Source: https://en.wikipedia.org/wiki/Retrieval-augmented_generation
> License: CC BY-SA 4.0 (Wikipedia)

From Wikipedia, the free encyclopedia
Type of information retrieval using LLMs
Retrieval-augmented generation(RAG) is a technique that enableslarge language models(LLMs) to retrieve and incorporate new information from external data sources.[1]With RAG, LLMs first refer to a specified set of documents, then respond to user queries. These documents supplement information from the LLM's pre-existingtraining data.[2]This allows LLMs to use domain-specific and/or updated information that is not available in the training data.[2]For example, this enables LLM-basedchatbotsto access internal company data or generate responses based on authoritative sources. The technique was first proposed in 2020 and has since become a widely adopted approach in modern AI systems.

Retrieval-augmented generation
(
RAG
) is a technique that enables
large language models
(LLMs) to retrieve and incorporate new information from external data sources.
[
1
]
With RAG, LLMs first refer to a specified set of documents, then respond to user queries. These documents supplement information from the LLM's pre-existing
training data
.
[
2
]
This allows LLMs to use domain-specific and/or updated information that is not available in the training data.
[
2
]
For example, this enables LLM-based
chatbots
to access internal company data or generate responses based on authoritative sources. The technique was first proposed in 2020 and has since become a widely adopted approach in modern AI systems.
RAG improves LLMs by incorporatinginformation retrievalbefore generating responses.[3]Unlike LLMs that rely on static training data, RAG pulls relevant text from databases, uploaded documents, or web sources.[1]According toArs Technica, "RAG is a way of improving LLM performance, in essence by blending the LLM process with a web search or other document look-up process to help LLMs stick to the facts." This method helps reduceAI hallucinations,[3]which have caused chatbots to describe policies that don't exist, or recommend nonexistent legal cases to lawyers that are looking for citations to support their arguments.[4]

RAG improves LLMs by incorporating
information retrieval
before generating responses.
[
3
]
Unlike LLMs that rely on static training data, RAG pulls relevant text from databases, uploaded documents, or web sources.
[
1
]
According to
Ars Technica
, "RAG is a way of improving LLM performance, in essence by blending the LLM process with a web search or other document look-up process to help LLMs stick to the facts." This method helps reduce
AI hallucinations
,
[
3
]
which have caused chatbots to describe policies that don't exist, or recommend nonexistent legal cases to lawyers that are looking for citations to support their arguments.
[
4
]
RAG also reduces the need to retrain LLMs with new data, saving on computational and financial costs.[1]Beyond efficiency gains, RAG also allows LLMs to include sources in their responses, so users can verify the cited sources. This provides greater transparency, as users can cross-check retrieved content to ensure accuracy and relevance.

RAG also reduces the need to retrain LLMs with new data, saving on computational and financial costs.
[
1
]
Beyond efficiency gains, RAG also allows LLMs to include sources in their responses, so users can verify the cited sources. This provides greater transparency, as users can cross-check retrieved content to ensure accuracy and relevance.
The term retrieval-augmented generation (RAG) was introduced in a 2020 paper that described combining a parametric language model with a non-parametric external memory accessed through retrieval at inference time.[3]

The term retrieval-augmented generation (RAG) was introduced in a 2020 paper that described combining a parametric language model with a non-parametric external memory accessed through retrieval at inference time.
[
3
]

## RAG and LLM limitations

RAG and LLM limitations
[
edit
]
LLMs can provide incorrect information. For example, when Google first demonstrated its LLM tool "Google Bard" (later re-branded to Gemini), the LLM provided incorrect information about theJames Webb Space Telescope. This error contributed to a $100 billion decline inGoogle'sstock value.[4]RAG is used to prevent these errors, but it does not solve all the problems. For example, LLMs can generate misinformation even when pulling from factually correct sources if they misinterpret the context.MIT Technology Reviewgives the example of an AI-generated response stating, "The United States has had one Muslim president, Barack Hussein Obama." The model retrieved this from the rhetorical chapter title "Barack Hussein Obama: America's First Muslim President?" in the bookFaith in the New Millennium: The Future of Religion and American Politics.[5]The LLM did not "know" or "understand" the context of the title, generating a false statement.[2]

LLMs can provide incorrect information. For example, when Google first demonstrated its LLM tool "
Google Bard
" (later re-branded to Gemini), the LLM provided incorrect information about the
James Webb Space Telescope
. This error contributed to a $100 billion decline in
Google's
stock value.
[
4
]
RAG is used to prevent these errors, but it does not solve all the problems. For example, LLMs can generate misinformation even when pulling from factually correct sources if they misinterpret the context.
MIT Technology Review
gives the example of an AI-generated response stating, "The United States has had one Muslim president, Barack Hussein Obama." The model retrieved this from the rhetorical chapter title "Barack Hussein Obama: America's First Muslim President?" in the book
Faith in the New Millennium: The Future of Religion and American Politics
.
[
5
]
The LLM did not "know" or "understand" the context of the title, generating a false statement.
[
2
]
LLMs with RAG are programmed to prioritize new information. This technique has been called "prompt stuffing." Without prompt stuffing, the LLM's input is generated by a user; with prompt stuffing, additional relevant context is added to this input to guide the model's response. This approach provides the LLM with key information early in the prompt, encouraging it to prioritize the supplied data over pre-existing training knowledge.[6]

LLMs with RAG are programmed to prioritize new information. This technique has been called "prompt stuffing." Without prompt stuffing, the LLM's input is generated by a user; with prompt stuffing, additional relevant context is added to this input to guide the model's response. This approach provides the LLM with key information early in the prompt, encouraging it to prioritize the supplied data over pre-existing training knowledge.
[
6
]

## Process

Process
[
edit
]
Retrieval-augmented generation (RAG) enhanceslarge language models(LLMs) by incorporating aninformation-retrievalmechanism that allows models to access and utilize additional data beyond their original training set.Ars Technicanotes that "when new information becomes available, rather than having to retrain the model, all that's needed is to augment the model's external knowledge base with the updated information" ("augmentation").[4]IBM states that "in the generative phase, the LLM draws from the augmented prompt and its internal representation of its training data to synthesize" an answer.[1]

Retrieval-augmented generation (RAG) enhances
large language models
(LLMs) by incorporating an
information-retrieval
mechanism that allows models to access and utilize additional data beyond their original training set.
Ars Technica
notes that "when new information becomes available, rather than having to retrain the model, all that's needed is to augment the model's external knowledge base with the updated information" ("augmentation").
[
4
]
IBM states that "in the generative phase, the LLM draws from the augmented prompt and its internal representation of its training data to synthesize" an answer.
[
1
]

### RAG key stages

RAG key stages
[
edit
]
Overview of RAG process, combining external documents and user input into an LLM prompt to get tailored output
Typically, the data to be referenced is converted into LLMembeddings, numerical representations in the form of a large vector space. RAG can be used on unstructured (usually text), semi-structured, or structured data (for exampleknowledge graphs). These embeddings are then stored in avector databaseto allow fordocument retrieval.

Typically, the data to be referenced is converted into LLM
embeddings
, numerical representations in the form of a large vector space. RAG can be used on unstructured (usually text), semi-structured, or structured data (for example
knowledge graphs
). These embeddings are then stored in a
vector database
to allow for
document retrieval
.
Given a user query, a document retriever is first called to select the most relevant documents that will be used to augment the query.[2][3]This comparison can be done using a variety of methods, which depend in part on the type of indexing used.[1]

Given a user query, a document retriever is first called to select the most relevant documents that will be used to augment the query.
[
2
]
[
3
]
This comparison can be done using a variety of methods, which depend in part on the type of indexing used.
[
1
]
The model feeds this relevant retrieved information into the LLM viaprompt engineeringof the user's original query. Newer implementations (as of 2023[update]) can also incorporate specific augmentation modules with abilities such as expanding queries into multiple domains and using memory and self-improvement to learn from previous retrievals.[citation needed]

The model feeds this relevant retrieved information into the LLM via
prompt engineering
of the user's original query. Newer implementations (as of 2023
[update]
) can also incorporate specific augmentation modules with abilities such as expanding queries into multiple domains and using memory and self-improvement to learn from previous retrievals.
[
citation needed
]
Finally, the LLM can generate output based on both the query and the retrieved documents.[2][3]Some models incorporate extra steps to improve output, such as the re-ranking of retrieved information, context selection, andfine-tuning.

Finally, the LLM can generate output based on both the query and the retrieved documents.
[
2
]
[
3
]
Some models incorporate extra steps to improve output, such as the re-ranking of retrieved information, context selection, and
fine-tuning
.

## Applications

Applications
[
edit
]
Retrieval-augmented generation is used in applications where generated responses need to be grounded in external or frequently updated information.[citation needed]

Retrieval-augmented generation is used in applications where generated responses need to be grounded in external or frequently updated information.
[
citation needed
]
In healthcare, RAG has been studied as a way to ground large language model outputs in external medical knowledge sources, although reviews have noted continuing challenges around evaluation, ethics, and clinical reliability.[7]

In healthcare, RAG has been studied as a way to ground large language model outputs in external medical knowledge sources, although reviews have noted continuing challenges around evaluation, ethics, and clinical reliability.
[
7
]

## Improvements

Improvements
[
edit
]
Improvements to the basic process above can be applied at different stages in the RAG flow.

Improvements to the basic process above can be applied at different stages in the RAG flow.

### Encoder

Encoder
[
edit
]
These methods focus on the encoding of text as either dense or sparse vectors.Sparse vectors, which encode the identity of a word, are typicallydictionary-length and contain mostly zeros.Dense vectors, which encode meaning, are more compact and contain fewer zeros. Various enhancements can improve the way similarities are calculated in the vector stores (databases).[8]

These methods focus on the encoding of text as either dense or sparse vectors.
Sparse vectors
, which encode the identity of a word, are typically
dictionary
-length and contain mostly zeros.
Dense vectors
, which encode meaning, are more compact and contain fewer zeros. Various enhancements can improve the way similarities are calculated in the vector stores (databases).
[
8
]
- Performance improves by optimizing how vector similarities are calculated.Dot productsenhance similarity scoring, whileapproximate nearest neighbor(ANN) searches improve retrieval efficiency overK-nearest neighbors(KNN) searches.[9]
Performance improves by optimizing how vector similarities are calculated.
Dot products
enhance similarity scoring, while
approximate nearest neighbor
(ANN) searches improve retrieval efficiency over
K-nearest neighbors
(KNN) searches.
[
9
]
- Accuracy may be improved with Late Interactions, which allow the system to compare words more precisely after retrieval. This helps refine document ranking and improve search relevance.[10]
Accuracy may be improved with Late Interactions, which allow the system to compare words more precisely after retrieval. This helps refine document ranking and improve search relevance.
[
10
]
- Hybrid vector approaches may be used to combine dense vector representations with sparseone-hotvectors, taking advantage of the computational efficiency of sparse dot products over dense vector operations.[8]
Hybrid vector approaches may be used to combine dense vector representations with sparse
one-hot
vectors, taking advantage of the computational efficiency of sparse dot products over dense vector operations.
[
8
]
- Other retrieval techniques focus on improving accuracy by refining how documents are selected. Some retrieval methods combine sparse representations, such as SPLADE, with query expansion strategies to improve search accuracy and recall.[11]
Other retrieval techniques focus on improving accuracy by refining how documents are selected. Some retrieval methods combine sparse representations, such as SPLADE, with query expansion strategies to improve search accuracy and recall.
[
11
]

### Retriever-centric methods

Retriever-centric methods
[
edit
]
These methods aim to enhance the quality of document retrieval in vector databases:

These methods aim to enhance the quality of document retrieval in vector databases:
- Pre-training the retriever using theInverse Cloze Task(ICT), a technique that helps the model learn retrieval patterns by predicting masked text within documents.[12]
Pre-training the retriever using the
Inverse Cloze Task
(ICT), a technique that helps the model learn retrieval patterns by predicting masked text within documents.
[
12
]
- Supervised retriever optimization aligns retrieval probabilities with the generator model's likelihood distribution. This involves retrieving the top-k vectors for a given prompt, scoring the generated response'sperplexity, and minimizingKL divergencebetween the retriever's selections and the model's likelihoods to refine retrieval.[13]
Supervised retriever optimization aligns retrieval probabilities with the generator model's likelihood distribution. This involves retrieving the top-k vectors for a given prompt, scoring the generated response's
perplexity
, and minimizing
KL divergence
between the retriever's selections and the model's likelihoods to refine retrieval.
[
13
]
- Reranking techniques can refine retriever performance by prioritizing the most relevant retrieved documents during training.[14]
Reranking techniques can refine retriever performance by prioritizing the most relevant retrieved documents during training.
[
14
]

### Language model

Language model
[
edit
]
Retro language model for RAG.  Each Retro block consists of Attention, Chunked Cross Attention, and Feed Forward layers.  Black-lettered boxes show data being changed, and blue lettering shows the algorithm performing the changes.
By redesigning the language model with the retriever in mind, a 25-time smaller network can get comparable perplexity as its much larger counterparts.[15]Because it is trained from scratch, this method (Retro) incurs the high cost of training runs that the original RAG scheme avoided. The hypothesis is that by giving domain knowledge during training, Retro needs less focus on the domain and can devote its smaller weight resources only to language semantics. The redesigned language model is shown here.

By redesigning the language model with the retriever in mind, a 25-time smaller network can get comparable perplexity as its much larger counterparts.
[
15
]
Because it is trained from scratch, this method (Retro) incurs the high cost of training runs that the original RAG scheme avoided. The hypothesis is that by giving domain knowledge during training, Retro needs less focus on the domain and can devote its smaller weight resources only to language semantics. The redesigned language model is shown here.
It has been reported that Retro is not reproducible, so modifications were made to make it so.  The more reproducible version is called Retro++ and includes in-context RAG.[16]

It has been reported that Retro is not reproducible, so modifications were made to make it so.  The more reproducible version is called Retro++ and includes in-context RAG.
[
16
]

### Chunking

Chunking
[
edit
]
See also:
Chunking (computing)
Chunking involves various strategies for breaking up the data into vectors so the retriever can find details in it.

Chunking involves various strategies for breaking up the data into vectors so the retriever can find details in it.
Different data styles have patterns that correct chunking can take advantage of.
Three types of chunking strategies are:[citation needed]

Three types of chunking strategies are:
[
citation needed
]
- Fixed length with overlap. This is fast and easy. Overlapping consecutive chunks helps to maintain semantic context across chunks.
Fixed length with overlap. This is fast and easy. Overlapping consecutive chunks helps to maintain semantic context across chunks.
- Syntax-based chunks can break the document up into sentences. Libraries such asspaCyorNLTKcan also help.
Syntax-based chunks can break the document up into sentences. Libraries such as
spaCy
or
NLTK
can also help.
- File format-based chunking. Certain file types have natural chunks built in, and it's best to respect them. For example, code files are best chunked and vectorized as whole functions or classes. HTML files should leave <table> or base64 encoded <img> elements intact. Similar considerations should be taken for pdf files. Libraries such as Unstructured orLangChaincan assist with this method.
File format-based chunking. Certain file types have natural chunks built in, and it's best to respect them. For example, code files are best chunked and vectorized as whole functions or classes. HTML files should leave <table> or base64 encoded <img> elements intact. Similar considerations should be taken for pdf files. Libraries such as Unstructured or
LangChain
can assist with this method.

### Hybrid search

Hybrid search
[
edit
]
Sometimes vector database searches can miss key facts needed to answer a user's question. One way to mitigate this is to do a traditional text search, add those results to the text chunks linked to the retrieved vectors from the vector search, and feed the combined hybrid text into the language model for generation.[17]

Sometimes vector database searches can miss key facts needed to answer a user's question. One way to mitigate this is to do a traditional text search, add those results to the text chunks linked to the retrieved vectors from the vector search, and feed the combined hybrid text into the language model for generation.
[
17
]

## Challenges

Challenges
[
edit
]
RAG does not prevent hallucinations in LLMs. According toArs Technica, "It is not a direct solution because the LLM can still hallucinate around the source material in its response."[4]

RAG does not prevent hallucinations in LLMs. According to
Ars Technica
, "It is not a direct solution because the LLM can still hallucinate around the source material in its response."
[
4
]
While RAG improves the accuracy of large language models (LLMs), it does not eliminate all challenges. One limitation is that while RAG reduces the need for frequent model retraining, it does not remove it entirely. Additionally, LLMs may struggle to recognize when they lack sufficient information to provide a reliable response. Without specific training, models may generate answers even when they should indicate uncertainty. According toIBM, this issue can arise when the model lacks the ability to assess its own knowledge limitations.[1]

While RAG improves the accuracy of large language models (LLMs), it does not eliminate all challenges. One limitation is that while RAG reduces the need for frequent model retraining, it does not remove it entirely. Additionally, LLMs may struggle to recognize when they lack sufficient information to provide a reliable response. Without specific training, models may generate answers even when they should indicate uncertainty. According to
IBM
, this issue can arise when the model lacks the ability to assess its own knowledge limitations.
[
1
]

### RAG poisoning

RAG poisoning
[
edit
]
RAG systems may retrieve factually correct but misleading sources, leading to errors in interpretation. In some cases, an LLM may extract statements from a source without considering its context, resulting in an incorrect conclusion. Additionally, when faced with conflicting information, RAG models may struggle to determine which source is accurate. The worst case outcome of this limitation is that the model may combine details from multiple sources producing responses that merge outdated and updated information in a misleading manner. According to theMIT Technology Review, these issues occur because RAG systems may misinterpret the data they retrieve.[2]

RAG systems may retrieve factually correct but misleading sources, leading to errors in interpretation. In some cases, an LLM may extract statements from a source without considering its context, resulting in an incorrect conclusion. Additionally, when faced with conflicting information, RAG models may struggle to determine which source is accurate. The worst case outcome of this limitation is that the model may combine details from multiple sources producing responses that merge outdated and updated information in a misleading manner. According to the
MIT Technology Review
, these issues occur because RAG systems may misinterpret the data they retrieve.
[
2
]

## References

References
[
edit
]
- ^abcdef"What is retrieval-augmented generation?".IBM. 22 August 2023. Retrieved7 March2025.
^
a
b
c
d
e
f
"What is retrieval-augmented generation?"
.
IBM
. 22 August 2023
. Retrieved
7 March
2025
.
- ^abcdef"Why Google's AI Overviews gets things wrong".MIT Technology Review. 31 May 2024. Retrieved7 March2025.
^
a
b
c
d
e
f
"Why Google's AI Overviews gets things wrong"
.
MIT Technology Review
. 31 May 2024
. Retrieved
7 March
2025
.
- ^abcdeLewis, Patrick; Perez, Ethan; Piktus, Aleksandra; Petroni, Fabio; Karpukhin, Vladimir; Goyal, Naman; Küttler, Heinrich; Lewis, Mike; Yih, Wen-tau; Rocktäschel, Tim; Riedel, Sebastian; Kiela, Douwe (2020)."Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks".Advances in Neural Information Processing Systems.33. Curran Associates, Inc.:9459–9474.arXiv:2005.11401.
^
a
b
c
d
e
Lewis, Patrick; Perez, Ethan; Piktus, Aleksandra; Petroni, Fabio; Karpukhin, Vladimir; Goyal, Naman; Küttler, Heinrich; Lewis, Mike; Yih, Wen-tau; Rocktäschel, Tim; Riedel, Sebastian; Kiela, Douwe (2020).
"Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
.
Advances in Neural Information Processing Systems
.
33
. Curran Associates, Inc.:
9459–
9474.
arXiv
:
2005.11401
.
- ^abcd"Can a technology called RAG keep AI models from making stuff up?".Ars Technica. 6 June 2024. Retrieved7 March2025.
^
a
b
c
d
"Can a technology called RAG keep AI models from making stuff up?"
.
Ars Technica
. 6 June 2024
. Retrieved
7 March
2025
.
- ^Goetz, Rebecca Anne (2015). "Barack Hussein Obama: America's First Muslim President?". In Sutton, Matthew Avery; Dochuk, Darren (eds.).Faith in the New Millennium: The Future of Religion and American Politics. Oxford University Press.doi:10.1093/acprof:oso/9780199372690.003.0006.ISBN9780199372737.
^
Goetz, Rebecca Anne (2015). "Barack Hussein Obama: America's First Muslim President?". In Sutton, Matthew Avery; Dochuk, Darren (eds.).
Faith in the New Millennium: The Future of Religion and American Politics
. Oxford University Press.
doi
:
10.1093/acprof:oso/9780199372690.003.0006
.
ISBN
9780199372737
.
- ^"Mitigating LLM hallucinations in text summarisation".BBC. 20 June 2024. Retrieved7 March2025.
^
"Mitigating LLM hallucinations in text summarisation"
.
BBC
. 20 June 2024
. Retrieved
7 March
2025
.
- ^Amugongo, Lameck Mbangula; Mascheroni, Pietro; Brooks, Steven; Doering, Stefan; Seidel, Jan (2025-06-11)."Retrieval augmented generation for large language models in healthcare: A systematic review".PLOS Digital Health.4(6) e0000877.doi:10.1371/journal.pdig.0000877.PMC12157099.
^
Amugongo, Lameck Mbangula; Mascheroni, Pietro; Brooks, Steven; Doering, Stefan; Seidel, Jan (2025-06-11).
"Retrieval augmented generation for large language models in healthcare: A systematic review"
.
PLOS Digital Health
.
4
(6) e0000877.
doi
:
10.1371/journal.pdig.0000877
.
PMC
12157099
.
- ^abLuan, Yi; Eisenstein, Jacob; Toutanova, Kristina; Collins, Michael (26 April 2021)."Sparse, Dense, and Attentional Representations for Text Retrieval".Transactions of the Association for Computational Linguistics.9:329–345.arXiv:2005.00181.doi:10.1162/tacl_a_00369. Retrieved15 March2025.
^
a
b
Luan, Yi; Eisenstein, Jacob; Toutanova, Kristina; Collins, Michael (26 April 2021).
"Sparse, Dense, and Attentional Representations for Text Retrieval"
.
Transactions of the Association for Computational Linguistics
.
9
:
329–
345.
arXiv
:
2005.00181
.
doi
:
10.1162/tacl_a_00369
. Retrieved
15 March
2025
.
- ^"Information retrieval".Microsoft. 10 January 2025. Retrieved15 March2025.
^
"Information retrieval"
.
Microsoft
. 10 January 2025
. Retrieved
15 March
2025
.
- ^Khattab, Omar; Zaharia, Matei (2020)."ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT".Proceedings of the 43rd International ACM SIGIR Conference on Research and Development in Information Retrieval. pp.39–48.doi:10.1145/3397271.3401075.ISBN978-1-4503-8016-4.
^
Khattab, Omar; Zaharia, Matei (2020).
"ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT"
.
Proceedings of the 43rd International ACM SIGIR Conference on Research and Development in Information Retrieval
. pp.
39–
48.
doi
:
10.1145/3397271.3401075
.
ISBN
978-1-4503-8016-4
.
- ^Wang, Yup; Conroy, John M.; Molino, Neil; Yang, Julia; Green, Mike (2024)."Laboratory for Analytic Sciences in TREC 2024 Retrieval Augmented Generation Track".NIST TREC 2024. Retrieved15 March2025.
^
Wang, Yup; Conroy, John M.; Molino, Neil; Yang, Julia; Green, Mike (2024).
"Laboratory for Analytic Sciences in TREC 2024 Retrieval Augmented Generation Track"
.
NIST TREC 2024
. Retrieved
15 March
2025
.
- ^Lee, Kenton; Chang, Ming-Wei; Toutanova, Kristina (2019).""Latent Retrieval for Weakly Supervised Open Domain Question Answering""(PDF).
^
Lee, Kenton; Chang, Ming-Wei; Toutanova, Kristina (2019).
"
"Latent Retrieval for Weakly Supervised Open Domain Question Answering"
"
(PDF)
.
- ^Shi, Weijia; Min, Sewon; Yasunaga, Michihiro; Seo, Minjoon; James, Rich; Lewis, Mike; Zettlemoyer, Luke; Yih, Wen-tau (June 2024)."REPLUG: Retrieval-Augmented Black-Box Language Models".Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers). pp.8371–8384.arXiv:2301.12652.doi:10.18653/v1/2024.naacl-long.463. Retrieved16 March2025.
^
Shi, Weijia; Min, Sewon; Yasunaga, Michihiro; Seo, Minjoon; James, Rich; Lewis, Mike; Zettlemoyer, Luke; Yih, Wen-tau (June 2024).
"REPLUG: Retrieval-Augmented Black-Box Language Models"
.
Proceedings of the 2024 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies (Volume 1: Long Papers)
. pp.
8371–
8384.
arXiv
:
2301.12652
.
doi
:
10.18653/v1/2024.naacl-long.463
. Retrieved
16 March
2025
.
- ^Ram, Ori; Levine, Yoav; Dalmedigos, Itay; Muhlgay, Dor; Shashua, Amnon; Leyton-Brown, Kevin; Shoham, Yoav (2023)."In-Context Retrieval-Augmented Language Models".Transactions of the Association for Computational Linguistics.11:1316–1331.arXiv:2302.00083.doi:10.1162/tacl_a_00605. Retrieved16 March2025.
^
Ram, Ori; Levine, Yoav; Dalmedigos, Itay; Muhlgay, Dor; Shashua, Amnon; Leyton-Brown, Kevin; Shoham, Yoav (2023).
"In-Context Retrieval-Augmented Language Models"
.
Transactions of the Association for Computational Linguistics
.
11
:
1316–
1331.
arXiv
:
2302.00083
.
doi
:
10.1162/tacl_a_00605
. Retrieved
16 March
2025
.
- ^Borgeaud, Sebastian; Mensch, Arthur (2021)."Improving language models by retrieving from trillions of tokens"(PDF).
^
Borgeaud, Sebastian; Mensch, Arthur (2021).
"Improving language models by retrieving from trillions of tokens"
(PDF)
.
- ^Wang, Boxin; Ping, Wei; Xu, Peng; McAfee, Lawrence; Liu, Zihan; Shoeybi, Mohammad; Dong, Yi; Kuchaiev, Oleksii; Li, Bo; Xiao, Chaowei; Anandkumar, Anima; Catanzaro, Bryan (2023)."Shall We Pretrain Autoregressive Language Models with Retrieval? A Comprehensive Study".Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing. pp.7763–7786.doi:10.18653/v1/2023.emnlp-main.482.
^
Wang, Boxin; Ping, Wei; Xu, Peng; McAfee, Lawrence; Liu, Zihan; Shoeybi, Mohammad; Dong, Yi; Kuchaiev, Oleksii; Li, Bo; Xiao, Chaowei; Anandkumar, Anima; Catanzaro, Bryan (2023).
"Shall We Pretrain Autoregressive Language Models with Retrieval? A Comprehensive Study"
.
Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing
. pp.
7763–
7786.
doi
:
10.18653/v1/2023.emnlp-main.482
.
- ^Bruch, Sebastian; Gai, Siyu; Ingber, Amir (2023). "An Analysis of Fusion Functions for Hybrid Retrieval".ACM Transactions on Information Systems.42(1):1–35.arXiv:2210.11934.doi:10.1145/3596512.
^
Bruch, Sebastian; Gai, Siyu; Ingber, Amir (2023). "An Analysis of Fusion Functions for Hybrid Retrieval".
ACM Transactions on Information Systems
.
42
(1):
1–
35.
arXiv
:
2210.11934
.
doi
:
10.1145/3596512
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
NewPP limit report
Parsed by mw‐web.codfw.main‐7dbdc7fd5b‐w5ll2
Cached time: 20260626180809
Cache expiry: 21600
Cache expiry source: Template:As_of (#time)
Reduced expiry: true
Complications: [vary‐revision‐sha1, prevent‐selective‐update, show‐toc]
CPU time usage: 0.374 seconds
Real time usage: 0.478 seconds
Preprocessor visited node count: 2228/1000000
Revision size: 20057/2097152 bytes
Post‐expand include size: 128435/2097152 bytes
Template argument size: 3539/2097152 bytes
Highest expansion depth: 15/100
Expensive parser function count: 5/500
Unstrip recursion depth: 1/20
Unstrip post‐expand size: 87272/5000000 bytes
Lua time usage: 0.218/10.000 seconds
Lua memory usage: 5970076/52428800 bytes
Number of Wikibase entities loaded: 0/500
Transclusion expansion time report (%,ms,calls,template)
100.00%  363.474      1 -total
 23.53%   85.528      8 Template:Cite_web
 22.59%   82.117      5 Template:Navbox
 20.31%   73.813      1 Template:Generative_AI
 13.68%   49.708      1 Template:Short_description
  8.61%   31.282      2 Template:Pagetype
  8.26%   30.028      3 Template:Fix
  8.24%   29.967      5 Template:Cite_journal
  7.39%   26.860      1 Template:Citation_needed
  6.30%   22.887      4 Template:Cite_book
Render ID fcbe8b58-7189-11f1-80bb-45e0babf6aca
Saved in parser cache with key enwiki:pcache:75229858:|#|:idhash:canonical and timestamp 20260626180809 and revision id 1361250981. Rendering was triggered because: page_view
Retrieved from "
https://en.wikipedia.org/w/index.php?title=Retrieval-augmented_generation&oldid=1361250981
"
Categories
:
- Large language models
Large language models
- Natural language processing
Natural language processing
- Information retrieval systems
Information retrieval systems
- Generative AI
Generative AI
Hidden categories:
- Articles with short description
Articles with short description
- Short description is different from Wikidata
Short description is different from Wikidata
- Articles containing potentially dated statements from 2023
Articles containing potentially dated statements from 2023
- All articles containing potentially dated statements
All articles containing potentially dated statements
- All articles with unsourced statements
All articles with unsourced statements
- Articles with unsourced statements from June 2026
Articles with unsourced statements from June 2026
- Articles with unsourced statements from August 2025
Articles with unsourced statements from August 2025