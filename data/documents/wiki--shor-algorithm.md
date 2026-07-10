<!-- source: https://en.wikipedia.org/wiki/Shor%27s_algorithm -->
# Shor's algorithm

> Source: https://en.wikipedia.org/wiki/Shor%27s_algorithm
> License: CC BY-SA 4.0 (Wikipedia)

From Wikipedia, the free encyclopedia
Quantum algorithm for integer factorization
Shor's algorithmis aquantum algorithmfor finding theprime factorsof an integer. It was developed in 1994 by the American mathematicianPeter Shor.[1][2]It is one of the few known quantum algorithms with compelling potential applications and strong evidence of superpolynomial speedup compared to best known classical (non-quantum) algorithms.[3]However, beating classical computers may require quantum computers with millions of qubits due to the overhead caused byquantum error correction.[4]

Shor's algorithm
is a
quantum algorithm
for finding the
prime factors
of an integer. It was developed in 1994 by the American mathematician
Peter Shor
.
[
1
]
[
2
]
It is one of the few known quantum algorithms with compelling potential applications and strong evidence of superpolynomial speedup compared to best known classical (non-quantum) algorithms.
[
3
]
However, beating classical computers may require quantum computers with millions of qubits due to the overhead caused by
quantum error correction
.
[
4
]
Shor proposed multiple similar algorithms for solving thefactoring problem, thediscrete logarithm problem, and the period-finding problem. "Shor's algorithm" usually refers to the factoring algorithm, but may refer to any of the three algorithms. The discrete logarithm algorithm and the factoring algorithm are instances of the period-finding algorithm, and all three are instances of thehidden subgroup problem.

Shor proposed multiple similar algorithms for solving the
factoring problem
, the
discrete logarithm problem
, and the period-finding problem. "Shor's algorithm" usually refers to the factoring algorithm, but may refer to any of the three algorithms. The discrete logarithm algorithm and the factoring algorithm are instances of the period-finding algorithm, and all three are instances of the
hidden subgroup problem
.
On a quantum computer, to factor an integerN{\displaystyle N}, Shor's algorithm runs inpolynomial time, meaning the time taken is polynomial inlog⁡N{\displaystyle \log N}.[5]It takesquantum gatesof orderO((log⁡N)2(log⁡log⁡N)(log⁡log⁡log⁡N)){\displaystyle O\!\left((\log N)^{2}(\log \log N)(\log \log \log N)\right)}using fast multiplication,[6]or evenO((log⁡N)2(log⁡log⁡N)){\displaystyle O\!\left((\log N)^{2}(\log \log N)\right)}using the asymptotically fastest multiplication algorithm currently known due to Harvey andvan der Hoeven,[7]thus demonstrating that theinteger factorizationproblem is incomplexity classBQP. Shor's algorithm is asymptotically faster than the most scalable classical factoring algorithm, thegeneral number field sieve, which works insub-exponential time:O(e1.9(log⁡N)1/3(log⁡log⁡N)2/3){\displaystyle O\!\left(e^{1.9(\log N)^{1/3}(\log \log N)^{2/3}}\right)}.[8]

On a quantum computer, to factor an integer
N
{\displaystyle N}
, Shor's algorithm runs in
polynomial time
, meaning the time taken is polynomial in
log
⁡
⁡
N
{\displaystyle \log N}
.
[
5
]
It takes
quantum gates
of order
O
(
(
log
⁡
⁡
N
)
2
(
log
⁡
⁡
log
⁡
⁡
N
)
(
log
⁡
⁡
log
⁡
⁡
log
⁡
⁡
N
)
)
{\displaystyle O\!\left((\log N)^{2}(\log \log N)(\log \log \log N)\right)}
using fast multiplication,
[
6
]
or even
O
(
(
log
⁡
⁡
N
)
2
(
log
⁡
⁡
log
⁡
⁡
N
)
)
{\displaystyle O\!\left((\log N)^{2}(\log \log N)\right)}
using the asymptotically fastest multiplication algorithm currently known due to Harvey and
van der Hoeven
,
[
7
]
thus demonstrating that the
integer factorization
problem is in
complexity class
BQP
. Shor's algorithm is asymptotically faster than the most scalable classical factoring algorithm, the
general number field sieve
, which works in
sub-exponential time
:
O
(
e
1.9
(
log
⁡
⁡
N
)
1
/
3
(
log
⁡
⁡
log
⁡
⁡
N
)
2
/
3
)
{\displaystyle O\!\left(e^{1.9(\log N)^{1/3}(\log \log N)^{2/3}}\right)}
.
[
8
]

## Feasibility and implications

Feasibility and implications
[
edit
]
Diagram presenting the encryption and the decryption of a document using asymmetric cryptography. Some forms of encryption (including asymmetric cryptography) are at risk of being broken by future quantum computers.
Assuming a quantum computer with a sufficient number ofqubitscould operate without succumbing toquantum noiseand otherquantum-decoherencephenomena, then Shor's algorithm could be used to breakpublic-key cryptographyschemes, such as

Assuming a quantum computer with a sufficient number of
qubits
could operate without succumbing to
quantum noise
and other
quantum-decoherence
phenomena, then Shor's algorithm could be used to break
public-key cryptography
schemes, such as
- TheRSAscheme
The
RSA
scheme
- The finite-fieldDiffie–Hellmankey exchange
The finite-field
Diffie–Hellman
key exchange
- Theelliptic-curve Diffie–Hellmankey exchange[9]
The
elliptic-curve Diffie–Hellman
key exchange
[
9
]
RSA can be broken if factoring large integers is computationally feasible. As far as is known, this is not possible using classical (non-quantum) computers; no classical algorithm is known that can factor integers in polynomial time. However, Shor's algorithm shows that factoring integers can be done with a polynomial complexity circuit on an ideal quantum computer. Thus, it might be feasible to defeat RSA by constructing a large enough quantum computer. This was a powerful motivator for the design and construction of quantum computers, and for the study of new quantum-computer algorithms. It has also facilitated research on new cryptosystems that are secure from quantum computers, collectively calledpost-quantum cryptography(PQC).

RSA can be broken if factoring large integers is computationally feasible. As far as is known, this is not possible using classical (non-quantum) computers; no classical algorithm is known that can factor integers in polynomial time. However, Shor's algorithm shows that factoring integers can be done with a polynomial complexity circuit on an ideal quantum computer. Thus, it might be feasible to defeat RSA by constructing a large enough quantum computer. This was a powerful motivator for the design and construction of quantum computers, and for the study of new quantum-computer algorithms. It has also facilitated research on new cryptosystems that are secure from quantum computers, collectively called
post-quantum cryptography
(PQC).

### Physical implementation

Physical implementation
[
edit
]
As of 2026, the high error rates of quantum computers and limited number of physical qubits available forquantum error correction, laboratory demonstrations of Shor's algorithm obtain correct results in only a fraction of attempts, and have only succeeded with smallsemiprimes.

As of 2026, the high error rates of quantum computers and limited number of physical qubits available for
quantum error correction
, laboratory demonstrations of Shor's algorithm obtain correct results in only a fraction of attempts, and have only succeeded with small
semiprimes
.
In 2001, Shor's algorithm was demonstrated by a group atIBM, who factored15{\displaystyle 15}into3×5{\displaystyle 3\times 5}, using anNMR implementationof a quantum computer with seven qubits.[10]After IBM's implementation, two independent groups implemented Shor's algorithm usingphotonicqubits, emphasizing that multi-qubitentanglementwas observed when running Shor's algorithm circuits.[11][12]In 2012, the factorization of15{\displaystyle 15}was performed with solid-state qubits.[13]Later, in 2012, the factorization of21{\displaystyle 21}was achieved.[14]In 2016, the factorization of15{\displaystyle 15}was performed again using trapped-ion qubits.[15]However, none of these demonstrations fulfill the requirements of Shor’s algorithm: they compile the circuit using prior knowledge of the solution, and some have even oversimplified the algorithm in a way that makes it equivalent to coin flipping.[16]

In 2001, Shor's algorithm was demonstrated by a group at
IBM
, who factored
15
{\displaystyle 15}
into
3
×
×
5
{\displaystyle 3\times 5}
, using an
NMR implementation
of a quantum computer with seven qubits.
[
10
]
After IBM's implementation, two independent groups implemented Shor's algorithm using
photonic
qubits, emphasizing that multi-qubit
entanglement
was observed when running Shor's algorithm circuits.
[
11
]
[
12
]
In 2012, the factorization of
15
{\displaystyle 15}
was performed with solid-state qubits.
[
13
]
Later, in 2012, the factorization of
21
{\displaystyle 21}
was achieved.
[
14
]
In 2016, the factorization of
15
{\displaystyle 15}
was performed again using trapped-ion qubits.
[
15
]
However, none of these demonstrations fulfill the requirements of Shor’s algorithm: they compile the circuit using prior knowledge of the solution, and some have even oversimplified the algorithm in a way that makes it equivalent to coin flipping.
[
16
]

## Algorithm

Algorithm
[
edit
]
The problem that we are trying to solve is:given an oddcomposite numberN{\displaystyle N}, find itsinteger factors.

The problem that we are trying to solve is:
given an odd
composite number
N
{\displaystyle N}
, find its
integer factors
.
To achieve this, Shor's algorithm consists of two parts:

To achieve this, Shor's algorithm consists of two parts:
- A classical reduction of the factoring problem to the problem oforder-finding. This reduction is similar to that used for otherfactoring algorithms, such as thequadratic sieve.
A classical reduction of the factoring problem to the problem of
order
-finding. This reduction is similar to that used for other
factoring algorithms
, such as the
quadratic sieve
.
- A quantum algorithm to solve the order-finding problem.
A quantum algorithm to solve the order-finding problem.

### Classical reduction

Classical reduction
[
edit
]
A complete factoring algorithm is possible if we're able to efficiently factor arbitraryN{\displaystyle N}into just two integersp{\displaystyle p}andq{\displaystyle q}greater than 1, since if eitherp{\displaystyle p}orq{\displaystyle q}are not prime, then the factoring algorithm can in turn be run on those until only primes remain.

A complete factoring algorithm is possible if we're able to efficiently factor arbitrary
N
{\displaystyle N}
into just two integers
p
{\displaystyle p}
and
q
{\displaystyle q}
greater than 1, since if either
p
{\displaystyle p}
or
q
{\displaystyle q}
are not prime, then the factoring algorithm can in turn be run on those until only primes remain.
A basic observation is that, usingEuclid's algorithm, we can always compute theGCDbetween two integers efficiently. In particular, this means we can check efficiently whetherN{\displaystyle N}is even, in which case 2 is trivially a factor. Let us thus assume thatN{\displaystyle N}is odd for the remainder of this discussion. Afterwards, we can use efficient classical algorithms to check whetherN{\displaystyle N}is aprime power.[17]For prime powers, efficient classical factorization algorithms exist,[18]hence the rest of the quantum algorithm may assume thatN{\displaystyle N}is not a prime power.

A basic observation is that, using
Euclid's algorithm
, we can always compute the
GCD
between two integers efficiently. In particular, this means we can check efficiently whether
N
{\displaystyle N}
is even, in which case 2 is trivially a factor. Let us thus assume that
N
{\displaystyle N}
is odd for the remainder of this discussion. Afterwards, we can use efficient classical algorithms to check whether
N
{\displaystyle N}
is a
prime power
.
[
17
]
For prime powers, efficient classical factorization algorithms exist,
[
18
]
hence the rest of the quantum algorithm may assume that
N
{\displaystyle N}
is not a prime power.
If those easy cases do not produce a nontrivial factor ofN{\displaystyle N}, the algorithm proceeds to handle the remaining case. We pick a random integer2≤a<N.{\displaystyle 2\leq a<N{.}}A possible nontrivial divisor ofN{\displaystyle N}can be found by computinggcd(a,N){\displaystyle \gcd(a,N)}, which can be done classically and efficiently using theEuclidean algorithm. If this produces a nontrivial factor (meaninggcd(a,N)≠1{\displaystyle \gcd(a,N)\neq 1}), the algorithm is finished, and the other nontrivial factor isN/gcd(a,N){\displaystyle N/\gcd(a,N)}. If a nontrivial factor was not identified, then this means thatN{\displaystyle N}and the choice ofa{\displaystyle a}arecoprime, soa{\displaystyle a}is contained in themultiplicative group of integers moduloN{\displaystyle N}, having amultiplicative inversemoduloN{\displaystyle N}. Thus,a{\displaystyle a}has amultiplicative orderr{\displaystyle r}moduloN{\displaystyle N}, meaning

If those easy cases do not produce a nontrivial factor of
N
{\displaystyle N}
, the algorithm proceeds to handle the remaining case. We pick a random integer
2
≤
≤
a
<
N
.
{\displaystyle 2\leq a<N{.}}
A possible nontrivial divisor of
N
{\displaystyle N}
can be found by computing
gcd
(
a
,
N
)
{\displaystyle \gcd(a,N)}
, which can be done classically and efficiently using the
Euclidean algorithm
. If this produces a nontrivial factor (meaning
gcd
(
a
,
N
)
≠
≠
1
{\displaystyle \gcd(a,N)\neq 1}
), the algorithm is finished, and the other nontrivial factor is
N
/
gcd
(
a
,
N
)
{\displaystyle N/\gcd(a,N)}
. If a nontrivial factor was not identified, then this means that
N
{\displaystyle N}
and the choice of
a
{\displaystyle a}
are
coprime
, so
a
{\displaystyle a}
is contained in the
multiplicative group of integers modulo
N
{\displaystyle N}
, having a
multiplicative inverse
modulo
N
{\displaystyle N}
. Thus,
a
{\displaystyle a}
has a
multiplicative order
r
{\displaystyle r}
modulo
N
{\displaystyle N}
, meaning
a
r
≡
≡
1
mod
N
,
{\displaystyle a^{r}\equiv 1{\bmod {N}},}
andr{\displaystyle r}is the smallest positive integer satisfying this congruence.

and
r
{\displaystyle r}
is the smallest positive integer satisfying this congruence.
The quantum subroutine findsr{\displaystyle r}. It can be seen from the congruence thatN{\displaystyle N}dividesar−1{\displaystyle a^{r}-1}, writtenN∣ar−1{\displaystyle N\mid a^{r}-1}. This can be factored usingdifference of squares:N∣(ar/2−1)(ar/2+1).{\displaystyle N\mid (a^{r/2}-1)(a^{r/2}+1).}Since we have factored the expression in this way, the algorithm doesn't work for oddr{\displaystyle r}(becausear/2{\displaystyle a^{r/2}}must be an integer), meaning that the algorithm would have to restart with a newa{\displaystyle a}. Hereafter we can therefore assume thatr{\displaystyle r}is even. It cannot be the case thatN∣ar/2−1{\displaystyle N\mid a^{r/2}-1}, since this would implyar/2≡1modN{\displaystyle a^{r/2}\equiv 1{\bmod {N}}}, which would contradictorily imply thatr/2{\displaystyle r/2}would be the order ofa{\displaystyle a}, which was alreadyr{\displaystyle r}. At this point, it may or may not be the case thatN∣ar/2+1{\displaystyle N\mid a^{r/2}+1}. IfN{\displaystyle N}does not dividear/2+1{\displaystyle a^{r/2}+1}, then this means that we are able to find a nontrivial factor ofN{\displaystyle N}. We computed=gcd(N,ar/2−1).{\displaystyle d=\gcd(N,a^{r/2}-1).}Ifd=1{\displaystyle d=1}, thenN∣ar/2+1{\displaystyle N\mid a^{r/2}+1}was true, and a nontrivial factor ofN{\displaystyle N}cannot be achieved froma{\displaystyle a}, and the algorithm must restart with a newa{\displaystyle a}. Otherwise, we have found a nontrivial factor ofN{\displaystyle N}, with the other beingN/d{\displaystyle N/d}, and the algorithm is finished. For this step, it is also equivalent to computegcd(N,ar/2+1){\displaystyle \gcd(N,a^{r/2}+1)}; it will produce a nontrivial factor ifgcd(N,ar/2−1){\displaystyle \gcd(N,a^{r/2}-1)}is nontrivial, and will not if it's trivial (whereN∣ar/2+1{\displaystyle N\mid a^{r/2}+1}).

The quantum subroutine finds
r
{\displaystyle r}
. It can be seen from the congruence that
N
{\displaystyle N}
divides
a
r
−
−
1
{\displaystyle a^{r}-1}
, written
N
∣
∣
a
r
−
−
1
{\displaystyle N\mid a^{r}-1}
. This can be factored using
difference of squares
:
N
∣
∣
(
a
r
/
2
−
−
1
)
(
a
r
/
2
+
1
)
.
{\displaystyle N\mid (a^{r/2}-1)(a^{r/2}+1).}
Since we have factored the expression in this way, the algorithm doesn't work for odd
r
{\displaystyle r}
(because
a
r
/
2
{\displaystyle a^{r/2}}
must be an integer), meaning that the algorithm would have to restart with a new
a
{\displaystyle a}
. Hereafter we can therefore assume that
r
{\displaystyle r}
is even. It cannot be the case that
N
∣
∣
a
r
/
2
−
−
1
{\displaystyle N\mid a^{r/2}-1}
, since this would imply
a
r
/
2
≡
≡
1
mod
N
{\displaystyle a^{r/2}\equiv 1{\bmod {N}}}
, which would contradictorily imply that
r
/
2
{\displaystyle r/2}
would be the order of
a
{\displaystyle a}
, which was already
r
{\displaystyle r}
. At this point, it may or may not be the case that
N
∣
∣
a
r
/
2
+
1
{\displaystyle N\mid a^{r/2}+1}
. If
N
{\displaystyle N}
does not divide
a
r
/
2
+
1
{\displaystyle a^{r/2}+1}
, then this means that we are able to find a nontrivial factor of
N
{\displaystyle N}
. We compute
d
=
gcd
(
N
,
a
r
/
2
−
−
1
)
.
{\displaystyle d=\gcd(N,a^{r/2}-1).}
If
d
=
1
{\displaystyle d=1}
, then
N
∣
∣
a
r
/
2
+
1
{\displaystyle N\mid a^{r/2}+1}
was true, and a nontrivial factor of
N
{\displaystyle N}
cannot be achieved from
a
{\displaystyle a}
, and the algorithm must restart with a new
a
{\displaystyle a}
. Otherwise, we have found a nontrivial factor of
N
{\displaystyle N}
, with the other being
N
/
d
{\displaystyle N/d}
, and the algorithm is finished. For this step, it is also equivalent to compute
gcd
(
N
,
a
r
/
2
+
1
)
{\displaystyle \gcd(N,a^{r/2}+1)}
; it will produce a nontrivial factor if
gcd
(
N
,
a
r
/
2
−
−
1
)
{\displaystyle \gcd(N,a^{r/2}-1)}
is nontrivial, and will not if it's trivial (where
N
∣
∣
a
r
/
2
+
1
{\displaystyle N\mid a^{r/2}+1}
).
The algorithm restated shortly follows: letN{\displaystyle N}be odd, and not a prime power. We want to output two nontrivial factors ofN{\displaystyle N}.

The algorithm restated shortly follows: let
N
{\displaystyle N}
be odd, and not a prime power. We want to output two nontrivial factors of
N
{\displaystyle N}
.
- Pick a random number1<a<N{\displaystyle 1<a<N}.
Pick a random number
1
<
a
<
N
{\displaystyle 1<a<N}
.
- ComputeK=gcd(a,N){\displaystyle K=\gcd(a,N)}, thegreatest common divisorofa{\displaystyle a}andN{\displaystyle N}.
Compute
K
=
gcd
(
a
,
N
)
{\displaystyle K=\gcd(a,N)}
, the
greatest common divisor
of
a
{\displaystyle a}
and
N
{\displaystyle N}
.
- IfK≠1{\displaystyle K\neq 1}, thenK{\displaystyle K}is anontrivialfactor ofN{\displaystyle N}, with the other factor beingN/K{\displaystyle N/K}, and we are done.
If
K
≠
≠
1
{\displaystyle K\neq 1}
, then
K
{\displaystyle K}
is a
nontrivial
factor of
N
{\displaystyle N}
, with the other factor being
N
/
K
{\displaystyle N/K}
, and we are done.
- Otherwise, use the quantum subroutine to find the orderr{\displaystyle r}ofa{\displaystyle a}.
Otherwise, use the quantum subroutine to find the order
r
{\displaystyle r}
of
a
{\displaystyle a}
.
- Ifr{\displaystyle r}is odd, then go back to step 1.
If
r
{\displaystyle r}
is odd, then go back to step 1.
- Computeg=gcd(N,ar/2+1){\displaystyle g=\gcd(N,a^{r/2}+1)}. Ifg{\displaystyle g}is nontrivial, the other factor isN/g{\displaystyle N/g}, and we're done. Otherwise, go back to step 1.
Compute
g
=
gcd
(
N
,
a
r
/
2
+
1
)
{\displaystyle g=\gcd(N,a^{r/2}+1)}
. If
g
{\displaystyle g}
is nontrivial, the other factor is
N
/
g
{\displaystyle N/g}
, and we're done. Otherwise, go back to step 1.
It has been shown that this will be likely to succeed after a few runs.[2]In practice, a single call to the quantum order-finding subroutine is enough to completely factorN{\displaystyle N}with very high probability of success if one uses a more advanced reduction.[19]

It has been shown that this will be likely to succeed after a few runs.
[
2
]
In practice, a single call to the quantum order-finding subroutine is enough to completely factor
N
{\displaystyle N}
with very high probability of success if one uses a more advanced reduction.
[
19
]

### Quantum order-finding subroutine

Quantum order-finding subroutine
[
edit
]
The goal of the quantum subroutine of Shor's algorithm is, givencoprime integersN{\displaystyle N}and1<a<N{\displaystyle 1<a<N}, to find theorderr{\displaystyle r}ofa{\displaystyle a}moduloN{\displaystyle N}, the smallest positive integerr{\displaystyle r}such thatar≡1(modN){\displaystyle a^{r}\equiv 1{\pmod {N}}}. To achieve this, Shor's algorithm uses a quantum circuit involving two registers. The second register usesn{\displaystyle n}qubits, wheren{\displaystyle n}is the smallest integer such thatN≤2n{\displaystyle N\leq 2^{n}}, i.e.,n=⌈log2⁡N⌉{\displaystyle n=\left\lceil {\log _{2}N}\right\rceil }. The size of the first register determines how accurate of an approximation the circuit produces. It can be shown that using2n{\displaystyle 2n}qubits gives sufficient accuracy to findr{\displaystyle r}. The exact quantum circuit depends on the parametersa{\displaystyle a}andN{\displaystyle N}, which define the problem. The following description of the algorithm usesbra–ket notationto denote quantum states, and⊗{\displaystyle \otimes }to denote thetensor product.

The goal of the quantum subroutine of Shor's algorithm is, given
coprime integers
N
{\displaystyle N}
and
1
<
a
<
N
{\displaystyle 1<a<N}
, to find the
order
r
{\displaystyle r}
of
a
{\displaystyle a}
modulo
N
{\displaystyle N}
, the smallest positive integer
r
{\displaystyle r}
such that
a
r
≡
≡
1
(
mod
N
)
{\displaystyle a^{r}\equiv 1{\pmod {N}}}
. To achieve this, Shor's algorithm uses a quantum circuit involving two registers. The second register uses
n
{\displaystyle n}
qubits, where
n
{\displaystyle n}
is the smallest integer such that
N
≤
≤
2
n
{\displaystyle N\leq 2^{n}}
, i.e.,
n
=
⌈
log
2
⁡
⁡
N
⌉
{\displaystyle n=\left\lceil {\log _{2}N}\right\rceil }
. The size of the first register determines how accurate of an approximation the circuit produces. It can be shown that using
2
n
{\displaystyle 2n}
qubits gives sufficient accuracy to find
r
{\displaystyle r}
. The exact quantum circuit depends on the parameters
a
{\displaystyle a}
and
N
{\displaystyle N}
, which define the problem. The following description of the algorithm uses
bra–ket notation
to denote quantum states, and
⊗
⊗
{\displaystyle \otimes }
to denote the
tensor product
.
The algorithm consists of two main steps:

The algorithm consists of two main steps:
- Usequantum phase estimationwithunitary matrixU{\displaystyle U}representing the operation of multiplying bya{\displaystyle a}(moduloN{\displaystyle N}), and input state|0⟩⊗2n⊗|1⟩{\displaystyle |0\rangle ^{\otimes 2n}\otimes |1\rangle }(where the second register is|1⟩{\displaystyle |1\rangle }made fromn{\displaystyle n}qubits). Theeigenvaluesof thisU{\displaystyle U}encode information about the period, and|1⟩{\displaystyle |1\rangle }can be seen to be writable as a sum of its eigenvectors. Thanks to these properties, the quantum phase estimation stage gives as output a random integer of the formjr22n{\displaystyle {\frac {j}{r}}2^{2n}}for randomj=0,1,...,r−1{\displaystyle j=0,1,...,r-1}.
Use
quantum phase estimation
with
unitary matrix
U
{\displaystyle U}
representing the operation of multiplying by
a
{\displaystyle a}
(modulo
N
{\displaystyle N}
), and input state
|
0
⟩
⟩
⊗
⊗
2
n
⊗
⊗
|
1
⟩
⟩
{\displaystyle |0\rangle ^{\otimes 2n}\otimes |1\rangle }
(where the second register is
|
1
⟩
⟩
{\displaystyle |1\rangle }
made from
n
{\displaystyle n}
qubits). The
eigenvalues
of this
U
{\displaystyle U}
encode information about the period, and
|
1
⟩
⟩
{\displaystyle |1\rangle }
can be seen to be writable as a sum of its eigenvectors. Thanks to these properties, the quantum phase estimation stage gives as output a random integer of the form
j
r
2
2
n
{\displaystyle {\frac {j}{r}}2^{2n}}
for random
j
=
0
,
1
,
.
.
.
,
r
−
−
1
{\displaystyle j=0,1,...,r-1}
.
- Use thecontinued fractions algorithmto extract the periodr{\displaystyle r}from the measurement outcomes obtained in the previous stage. This is a procedure to post-process (with a classical computer) the measurement data obtained from measuring the output quantum states, and retrieve the period.
Use the
continued fractions algorithm
to extract the period
r
{\displaystyle r}
from the measurement outcomes obtained in the previous stage. This is a procedure to post-process (with a classical computer) the measurement data obtained from measuring the output quantum states, and retrieve the period.
The connection with quantum phase estimation was not discussed in the original formulation of Shor's algorithm,[2]but was later proposed byAlexei Kitaev.[20]

The connection with quantum phase estimation was not discussed in the original formulation of Shor's algorithm,
[
2
]
but was later proposed by
Alexei Kitaev
.
[
20
]

#### Quantum phase estimation

Quantum phase estimation
[
edit
]
Quantum subroutine in Shor's algorithm
In general thequantum phase estimation algorithm, for any unitaryU{\displaystyle U}and eigenstate|ψ⟩{\displaystyle |\psi \rangle }such thatU|ψ⟩=e2πiθ|ψ⟩{\displaystyle U|\psi \rangle =e^{2\pi i\theta }|\psi \rangle }, sends input states|0⟩|ψ⟩{\displaystyle |0\rangle |\psi \rangle }to output states close to|ϕ⟩|ψ⟩{\displaystyle |\phi \rangle |\psi \rangle }, whereϕ{\displaystyle \phi }is a superposition of integers close to22nθ{\displaystyle 2^{2n}\theta }. In other words, it sends each eigenstate|ψj⟩{\displaystyle |\psi _{j}\rangle }ofU{\displaystyle U}to a state containing information close to the associated eigenvalue. For the purposes of quantum order-finding, we employ this strategy using the unitary defined by the actionU|k⟩={|ak(modN)⟩0≤k<N,|k⟩N≤k<2n.{\displaystyle U|k\rangle ={\begin{cases}|ak{\pmod {N}}\rangle &0\leq k<N,\\|k\rangle &N\leq k<2^{n}.\end{cases}}}The action ofU{\displaystyle U}on states|k⟩{\displaystyle |k\rangle }withN≤k<2n{\displaystyle N\leq k<2^{n}}is not crucial to the functioning of the algorithm, but needs to be included to ensure that the overall transformation is a well-defined quantum gate. Implementing the circuit for quantum phase estimation withU{\displaystyle U}requires being able to efficiently implement the gatesU2j{\displaystyle U^{2^{j}}}. This can be accomplished viamodular exponentiation, which is the slowest part of the algorithm.

In general the
quantum phase estimation algorithm
, for any unitary
U
{\displaystyle U}
and eigenstate
|
ψ
ψ
⟩
⟩
{\displaystyle |\psi \rangle }
such that
U
|
ψ
ψ
⟩
⟩
=
e
2
π
π
i
θ
θ
|
ψ
ψ
⟩
⟩
{\displaystyle U|\psi \rangle =e^{2\pi i\theta }|\psi \rangle }
, sends input states
|
0
⟩
⟩
|
ψ
ψ
⟩
⟩
{\displaystyle |0\rangle |\psi \rangle }
to output states close to
|
ϕ
ϕ
⟩
⟩
|
ψ
ψ
⟩
⟩
{\displaystyle |\phi \rangle |\psi \rangle }
, where
ϕ
ϕ
{\displaystyle \phi }
is a superposition of integers close to
2
2
n
θ
θ
{\displaystyle 2^{2n}\theta }
. In other words, it sends each eigenstate
|
ψ
ψ
j
⟩
⟩
{\displaystyle |\psi _{j}\rangle }
of
U
{\displaystyle U}
to a state containing information close to the associated eigenvalue. For the purposes of quantum order-finding, we employ this strategy using the unitary defined by the action
U
|
k
⟩
⟩
=
{
|
a
k
(
mod
N
)
⟩
⟩
0
≤
≤
k
<
N
,
|
k
⟩
⟩
N
≤
≤
k
<
2
n
.
{\displaystyle U|k\rangle ={\begin{cases}|ak{\pmod {N}}\rangle &0\leq k<N,\\|k\rangle &N\leq k<2^{n}.\end{cases}}}
The action of
U
{\displaystyle U}
on states
|
k
⟩
⟩
{\displaystyle |k\rangle }
with
N
≤
≤
k
<
2
n
{\displaystyle N\leq k<2^{n}}
is not crucial to the functioning of the algorithm, but needs to be included to ensure that the overall transformation is a well-defined quantum gate. Implementing the circuit for quantum phase estimation with
U
{\displaystyle U}
requires being able to efficiently implement the gates
U
2
j
{\displaystyle U^{2^{j}}}
. This can be accomplished via
modular exponentiation
, which is the slowest part of the algorithm.
The gate thus defined satisfiesUr=I{\displaystyle U^{r}=I}, which immediately implies that its eigenvalues are ther{\displaystyle r}-throots of unityωrk=e2πik/r{\displaystyle \omega _{r}^{k}=e^{2\pi ik/r}}. Furthermore, each eigenvalueωrj{\displaystyle \omega _{r}^{j}}has an eigenvector of the form|ψj⟩=r−1/2∑k=0r−1ωr−kj|ak⟩{\textstyle |\psi _{j}\rangle =r^{-1/2}\sum _{k=0}^{r-1}\omega _{r}^{-kj}|a^{k}\rangle }, and these eigenvectors are such that1r∑j=0r−1|ψj⟩=1r∑j=0r−1∑k=0r−1ωrjk|ak⟩=|1⟩+1r∑k=1r−1(∑j=0r−1ωrjk)|ak⟩=|1⟩,{\displaystyle {\begin{aligned}{\frac {1}{\sqrt {r}}}\sum _{j=0}^{r-1}|\psi _{j}\rangle &={\frac {1}{r}}\sum _{j=0}^{r-1}\sum _{k=0}^{r-1}\omega _{r}^{jk}|a^{k}\rangle \\&=|1\rangle +{\frac {1}{r}}\sum _{k=1}^{r-1}\left(\sum _{j=0}^{r-1}\omega _{r}^{jk}\right)|a^{k}\rangle =|1\rangle ,\end{aligned}}}where the last identity follows from thegeometric seriesformula, which implies∑j=0r−1ωrjk=0{\textstyle \sum _{j=0}^{r-1}\omega _{r}^{jk}=0}.

The gate thus defined satisfies
U
r
=
I
{\displaystyle U^{r}=I}
, which immediately implies that its eigenvalues are the
r
{\displaystyle r}
-th
roots of unity
ω
ω
r
k
=
e
2
π
π
i
k
/
r
{\displaystyle \omega _{r}^{k}=e^{2\pi ik/r}}
. Furthermore, each eigenvalue
ω
ω
r
j
{\displaystyle \omega _{r}^{j}}
has an eigenvector of the form
|
ψ
ψ
j
⟩
⟩
=
r
−
−
1
/
2
∑
∑
k
=
0
r
−
−
1
ω
ω
r
−
−
k
j
|
a
k
⟩
⟩
{\textstyle |\psi _{j}\rangle =r^{-1/2}\sum _{k=0}^{r-1}\omega _{r}^{-kj}|a^{k}\rangle }
, and these eigenvectors are such that
1
r
∑
∑
j
=
0
r
−
−
1
|
ψ
ψ
j
⟩
⟩
=
1
r
∑
∑
j
=
0
r
−
−
1
∑
∑
k
=
0
r
−
−
1
ω
ω
r
j
k
|
a
k
⟩
⟩
=
|
1
⟩
⟩
+
1
r
∑
∑
k
=
1
r
−
−
1
(
∑
∑
j
=
0
r
−
−
1
ω
ω
r
j
k
)
|
a
k
⟩
⟩
=
|
1
⟩
⟩
,
{\displaystyle {\begin{aligned}{\frac {1}{\sqrt {r}}}\sum _{j=0}^{r-1}|\psi _{j}\rangle &={\frac {1}{r}}\sum _{j=0}^{r-1}\sum _{k=0}^{r-1}\omega _{r}^{jk}|a^{k}\rangle \\&=|1\rangle +{\frac {1}{r}}\sum _{k=1}^{r-1}\left(\sum _{j=0}^{r-1}\omega _{r}^{jk}\right)|a^{k}\rangle =|1\rangle ,\end{aligned}}}
where the last identity follows from the
geometric series
formula, which implies
∑
∑
j
=
0
r
−
−
1
ω
ω
r
j
k
=
0
{\textstyle \sum _{j=0}^{r-1}\omega _{r}^{jk}=0}
.
Usingquantum phase estimationon an input state|0⟩⊗2n|ψj⟩{\displaystyle |0\rangle ^{\otimes 2n}|\psi _{j}\rangle }would then return the integer22nj/r{\displaystyle 2^{2n}j/r}with high probability. More precisely, the quantum phase estimation circuit sends|0⟩⊗2n|ψj⟩{\displaystyle |0\rangle ^{\otimes 2n}|\psi _{j}\rangle }to|ϕj⟩|ψj⟩{\displaystyle |\phi _{j}\rangle |\psi _{j}\rangle }such that the resulting probability distributionpk≡|⟨k|ϕj⟩|2{\displaystyle p_{k}\equiv |\langle k|\phi _{j}\rangle |^{2}}is peaked aroundk=22nj/r{\displaystyle k=2^{2n}j/r}, withp22nj/r≥4/π2≈0.4053{\displaystyle p_{2^{2n}j/r}\geq 4/\pi ^{2}\approx 0.4053}. This probability can be made arbitrarily close to 1 using extra qubits.

Using
quantum phase estimation
on an input state
|
0
⟩
⟩
⊗
⊗
2
n
|
ψ
ψ
j
⟩
⟩
{\displaystyle |0\rangle ^{\otimes 2n}|\psi _{j}\rangle }
would then return the integer
2
2
n
j
/
r
{\displaystyle 2^{2n}j/r}
with high probability. More precisely, the quantum phase estimation circuit sends
|
0
⟩
⟩
⊗
⊗
2
n
|
ψ
ψ
j
⟩
⟩
{\displaystyle |0\rangle ^{\otimes 2n}|\psi _{j}\rangle }
to
|
ϕ
ϕ
j
⟩
⟩
|
ψ
ψ
j
⟩
⟩
{\displaystyle |\phi _{j}\rangle |\psi _{j}\rangle }
such that the resulting probability distribution
p
k
≡
≡
|
⟨
⟨
k
|
ϕ
ϕ
j
⟩
⟩
|
2
{\displaystyle p_{k}\equiv |\langle k|\phi _{j}\rangle |^{2}}
is peaked around
k
=
2
2
n
j
/
r
{\displaystyle k=2^{2n}j/r}
, with
p
2
2
n
j
/
r
≥
≥
4
/
π
π
2
≈
≈
0.4053
{\displaystyle p_{2^{2n}j/r}\geq 4/\pi ^{2}\approx 0.4053}
. This probability can be made arbitrarily close to 1 using extra qubits.
Applying the above reasoning to the input|0⟩⊗2n|1⟩{\displaystyle |0\rangle ^{\otimes 2n}|1\rangle }, quantum phase estimation thus results in the evolution|0⟩⊗2n|1⟩=1r∑j=0r−1|0⟩⊗2n|ψj⟩→1r∑j=0r−1|ϕj⟩|ψj⟩.{\displaystyle |0\rangle ^{\otimes 2n}|1\rangle ={\frac {1}{\sqrt {r}}}\sum _{j=0}^{r-1}|0\rangle ^{\otimes 2n}|\psi _{j}\rangle \to {\frac {1}{\sqrt {r}}}\sum _{j=0}^{r-1}|\phi _{j}\rangle |\psi _{j}\rangle .}Measuring the first register, we now have a balanced probability1/r{\displaystyle 1/r}to find each|ϕj⟩{\displaystyle |\phi _{j}\rangle }, each one giving an integer approximation to22nj/r{\displaystyle 2^{2n}j/r}, which can be divided by22n{\displaystyle 2^{2n}}to get a decimal approximation forj/r{\displaystyle j/r}.

Applying the above reasoning to the input
|
0
⟩
⟩
⊗
⊗
2
n
|
1
⟩
⟩
{\displaystyle |0\rangle ^{\otimes 2n}|1\rangle }
, quantum phase estimation thus results in the evolution
|
0
⟩
⟩
⊗
⊗
2
n
|
1
⟩
⟩
=
1
r
∑
∑
j
=
0
r
−
−
1
|
0
⟩
⟩
⊗
⊗
2
n
|
ψ
ψ
j
⟩
⟩
→
→
1
r
∑
∑
j
=
0
r
−
−
1
|
ϕ
ϕ
j
⟩
⟩
|
ψ
ψ
j
⟩
⟩
.
{\displaystyle |0\rangle ^{\otimes 2n}|1\rangle ={\frac {1}{\sqrt {r}}}\sum _{j=0}^{r-1}|0\rangle ^{\otimes 2n}|\psi _{j}\rangle \to {\frac {1}{\sqrt {r}}}\sum _{j=0}^{r-1}|\phi _{j}\rangle |\psi _{j}\rangle .}
Measuring the first register, we now have a balanced probability
1
/
r
{\displaystyle 1/r}
to find each
|
ϕ
ϕ
j
⟩
⟩
{\displaystyle |\phi _{j}\rangle }
, each one giving an integer approximation to
2
2
n
j
/
r
{\displaystyle 2^{2n}j/r}
, which can be divided by
2
2
n
{\displaystyle 2^{2n}}
to get a decimal approximation for
j
/
r
{\displaystyle j/r}
.

#### Continued-fraction algorithm to retrieve the period

Continued-fraction algorithm to retrieve the period
[
edit
]
Then, we apply thecontinued-fractionalgorithm to find integersb{\displaystyle b}andc{\displaystyle c}, whereb/c{\displaystyle b/c}gives the best fraction approximation for the approximation measured from the circuit, forb,c<N{\displaystyle b,c<N}andcoprimeb{\displaystyle b}andc{\displaystyle c}. The number of qubits in the first register,2n{\displaystyle 2n}, which determines the accuracy of the approximation, guarantees thatbc=jr,{\displaystyle {\frac {b}{c}}={\frac {j}{r}},}given the best approximation from the superposition of|ϕj⟩{\displaystyle |\phi _{j}\rangle }was measured[2](which can be made arbitrarily likely by using extra bits and truncating the output). However, whileb{\displaystyle b}andc{\displaystyle c}are coprime, it may be the case thatj{\displaystyle j}andr{\displaystyle r}are not coprime. Because of that,b{\displaystyle b}andc{\displaystyle c}may have lost some factors that were inj{\displaystyle j}andr{\displaystyle r}. This can be remedied by rerunning the quantum order-finding subroutine an arbitrary number of times, to produce a list of fraction approximationsb1c1,b2c2,…,bscs,{\displaystyle {\frac {b_{1}}{c_{1}}},{\frac {b_{2}}{c_{2}}},\ldots ,{\frac {b_{s}}{c_{s}}},}wheres{\displaystyle s}is the number of times the subroutine was run. Eachck{\displaystyle c_{k}}will have different factors taken out of it because the circuit will (likely) have measured multiple different possible values ofj{\displaystyle j}. To recover the actualr{\displaystyle r}value, we can take theleast common multipleof eachck{\displaystyle c_{k}}:lcm⁡(c1,c2,…,cs).{\displaystyle \operatorname {lcm} (c_{1},c_{2},\ldots ,c_{s}).}The least common multiple will be the orderr{\displaystyle r}of the original integera{\displaystyle a}with high probability. In practice, a single run of the quantum order-finding subroutine is in general enough if more advanced post-processing is used.[21]

Then, we apply the
continued-fraction
algorithm to find integers
b
{\displaystyle b}
and
c
{\displaystyle c}
, where
b
/
c
{\displaystyle b/c}
gives the best fraction approximation for the approximation measured from the circuit, for
b
,
c
<
N
{\displaystyle b,c<N}
and
coprime
b
{\displaystyle b}
and
c
{\displaystyle c}
. The number of qubits in the first register,
2
n
{\displaystyle 2n}
, which determines the accuracy of the approximation, guarantees that
b
c
=
j
r
,
{\displaystyle {\frac {b}{c}}={\frac {j}{r}},}
given the best approximation from the superposition of
|
ϕ
ϕ
j
⟩
⟩
{\displaystyle |\phi _{j}\rangle }
was measured
[
2
]
(which can be made arbitrarily likely by using extra bits and truncating the output). However, while
b
{\displaystyle b}
and
c
{\displaystyle c}
are coprime, it may be the case that
j
{\displaystyle j}
and
r
{\displaystyle r}
are not coprime. Because of that,
b
{\displaystyle b}
and
c
{\displaystyle c}
may have lost some factors that were in
j
{\displaystyle j}
and
r
{\displaystyle r}
. This can be remedied by rerunning the quantum order-finding subroutine an arbitrary number of times, to produce a list of fraction approximations
b
1
c
1
,
b
2
c
2
,
…
…
,
b
s
c
s
,
{\displaystyle {\frac {b_{1}}{c_{1}}},{\frac {b_{2}}{c_{2}}},\ldots ,{\frac {b_{s}}{c_{s}}},}
where
s
{\displaystyle s}
is the number of times the subroutine was run. Each
c
k
{\displaystyle c_{k}}
will have different factors taken out of it because the circuit will (likely) have measured multiple different possible values of
j
{\displaystyle j}
. To recover the actual
r
{\displaystyle r}
value, we can take the
least common multiple
of each
c
k
{\displaystyle c_{k}}
:
lcm
⁡
⁡
(
c
1
,
c
2
,
…
…
,
c
s
)
.
{\displaystyle \operatorname {lcm} (c_{1},c_{2},\ldots ,c_{s}).}
The least common multiple will be the order
r
{\displaystyle r}
of the original integer
a
{\displaystyle a}
with high probability. In practice, a single run of the quantum order-finding subroutine is in general enough if more advanced post-processing is used.
[
21
]

#### Choosing the size of the first register

Choosing the size of the first register
[
edit
]
Phase estimation requires choosing the size of the first register to determine the accuracy of the algorithm, and for the quantum subroutine of Shor's algorithm,2n{\displaystyle 2n}qubits is sufficient to guarantee that the optimal bitstring measured from phase estimation (meaning the|k⟩{\displaystyle |k\rangle }wherek/22n{\textstyle k/2^{2n}}is the most accurate approximation of the phase from phase estimation) will allow the actual value ofr{\displaystyle r}to be recovered.

Phase estimation requires choosing the size of the first register to determine the accuracy of the algorithm, and for the quantum subroutine of Shor's algorithm,
2
n
{\displaystyle 2n}
qubits is sufficient to guarantee that the optimal bitstring measured from phase estimation (meaning the
|
k
⟩
⟩
{\displaystyle |k\rangle }
where
k
/
2
2
n
{\textstyle k/2^{2n}}
is the most accurate approximation of the phase from phase estimation) will allow the actual value of
r
{\displaystyle r}
to be recovered.
Each|ϕj⟩{\displaystyle |\phi _{j}\rangle }before measurement in Shor's algorithm represents a superposition of integers approximating22nj/r{\displaystyle 2^{2n}j/r}. Let|k⟩{\displaystyle |k\rangle }represent the most optimal integer in|ϕj⟩{\displaystyle |\phi _{j}\rangle }. The following theorem guarantees that the continued fractions algorithm will recoverj/r{\displaystyle j/r}fromk/22n{\displaystyle k/2^{2{n}}}:

Each
|
ϕ
ϕ
j
⟩
⟩
{\displaystyle |\phi _{j}\rangle }
before measurement in Shor's algorithm represents a superposition of integers approximating
2
2
n
j
/
r
{\displaystyle 2^{2n}j/r}
. Let
|
k
⟩
⟩
{\displaystyle |k\rangle }
represent the most optimal integer in
|
ϕ
ϕ
j
⟩
⟩
{\displaystyle |\phi _{j}\rangle }
. The following theorem guarantees that the continued fractions algorithm will recover
j
/
r
{\displaystyle j/r}
from
k
/
2
2
n
{\displaystyle k/2^{2{n}}}
:
Theorem—Ifj{\displaystyle j}andr{\displaystyle r}aren{\displaystyle n}bit integers, and|jr−ϕ|≤12r2{\displaystyle \left\vert {\frac {j}{r}}-\phi \right\vert \leq {\frac {1}{2r^{2}}}}then the continued fractions algorithm run onϕ{\displaystyle \phi }will recover bothjgcd(j,r){\textstyle {\frac {j}{\gcd(j,\;r)}}}andrgcd(j,r){\textstyle {\frac {r}{\gcd(j,\;r)}}}.

Theorem
—
If
j
{\displaystyle j}
and
r
{\displaystyle r}
are
n
{\displaystyle n}
bit integers, and
|
j
r
−
−
ϕ
ϕ
|
≤
≤
1
2
r
2
{\displaystyle \left\vert {\frac {j}{r}}-\phi \right\vert \leq {\frac {1}{2r^{2}}}}
then the continued fractions algorithm run on
ϕ
ϕ
{\displaystyle \phi }
will recover both
j
gcd
(
j
,
r
)
{\textstyle {\frac {j}{\gcd(j,\;r)}}}
and
r
gcd
(
j
,
r
)
{\textstyle {\frac {r}{\gcd(j,\;r)}}}
.
[3]Ask{\displaystyle k}is the optimal bitstring from phase estimation,k/22n{\displaystyle k/2^{2{n}}}is accurate toj/r{\displaystyle j/r}by2n{\displaystyle 2n}bits. Thus,|jr−k22n|≤122n+1≤12N2≤12r2{\displaystyle \left\vert {\frac {j}{r}}-{\frac {k}{2^{2n}}}\right\vert \leq {\frac {1}{2^{2{n}+1}}}\leq {\frac {1}{2N^{2}}}\leq {\frac {1}{2r^{2}}}}which implies that the continued fractions algorithm will recoverj{\displaystyle j}andr{\displaystyle r}(or with their greatest common divisor taken out).

[
3
]
As
k
{\displaystyle k}
is the optimal bitstring from phase estimation,
k
/
2
2
n
{\displaystyle k/2^{2{n}}}
is accurate to
j
/
r
{\displaystyle j/r}
by
2
n
{\displaystyle 2n}
bits. Thus,
|
j
r
−
−
k
2
2
n
|
≤
≤
1
2
2
n
+
1
≤
≤
1
2
N
2
≤
≤
1
2
r
2
{\displaystyle \left\vert {\frac {j}{r}}-{\frac {k}{2^{2n}}}\right\vert \leq {\frac {1}{2^{2{n}+1}}}\leq {\frac {1}{2N^{2}}}\leq {\frac {1}{2r^{2}}}}
which implies that the continued fractions algorithm will recover
j
{\displaystyle j}
and
r
{\displaystyle r}
(or with their greatest common divisor taken out).

### The bottleneck

The bottleneck
[
edit
]
The runtime bottleneck of Shor's algorithm is quantummodular exponentiation, which is by far slower than thequantum Fourier transformand classical pre-/post-processing. There are several approaches to constructing and optimizing circuits for modular exponentiation. The simplest and (currently) most practical approach is to mimic conventional arithmetic circuits withreversible gates, starting withripple-carry adders. Knowing the base and the modulus of exponentiation facilitates further optimizations.[22][23]Reversible circuits typically use on the order ofn3{\displaystyle n^{3}}gates forn{\displaystyle n}qubits. Alternative techniques asymptotically improve gate counts by usingquantum Fourier transforms, but are not competitive with fewer than 600 qubits owing to high constants.

The runtime bottleneck of Shor's algorithm is quantum
modular exponentiation
, which is by far slower than the
quantum Fourier transform
and classical pre-/post-processing. There are several approaches to constructing and optimizing circuits for modular exponentiation. The simplest and (currently) most practical approach is to mimic conventional arithmetic circuits with
reversible gates
, starting with
ripple-carry adders
. Knowing the base and the modulus of exponentiation facilitates further optimizations.
[
22
]
[
23
]
Reversible circuits typically use on the order of
n
3
{\displaystyle n^{3}}
gates for
n
{\displaystyle n}
qubits. Alternative techniques asymptotically improve gate counts by using
quantum Fourier transforms
, but are not competitive with fewer than 600 qubits owing to high constants.

## Period finding and discrete logarithms

Period finding and discrete logarithms
[
edit
]
Shor's algorithms for thediscrete logand the order finding problems are instances of an algorithm solving the period finding problem.[citation needed]All three are instances of thehidden subgroup problem.

Shor's algorithms for the
discrete log
and the order finding problems are instances of an algorithm solving the period finding problem.
[
citation needed
]
All three are instances of the
hidden subgroup problem
.

### Shor's algorithm for discrete logarithms

Shor's algorithm for discrete logarithms
[
edit
]
Given agroupG{\displaystyle G}with orderp{\displaystyle p}andgeneratorg∈G{\displaystyle g\in G}, suppose we know thatx=gr∈G{\displaystyle x=g^{r}\in G}, for somer∈Zp{\displaystyle r\in \mathbb {Z} _{p}}, and we wish to computer{\displaystyle r}, which is thediscrete logarithm:r=logg(x){\displaystyle r={\log _{g}}(x)}. Consider theabelian groupZp×Zp{\displaystyle \mathbb {Z} _{p}\times \mathbb {Z} _{p}}, where each factor corresponds to modular addition of values. Now, consider the function

Given a
group
G
{\displaystyle G}
with order
p
{\displaystyle p}
and
generator
g
∈
∈
G
{\displaystyle g\in G}
, suppose we know that
x
=
g
r
∈
∈
G
{\displaystyle x=g^{r}\in G}
, for some
r
∈
∈
Z
p
{\displaystyle r\in \mathbb {Z} _{p}}
, and we wish to compute
r
{\displaystyle r}
, which is the
discrete logarithm
:
r
=
log
g
(
x
)
{\displaystyle r={\log _{g}}(x)}
. Consider the
abelian group
Z
p
×
×
Z
p
{\displaystyle \mathbb {Z} _{p}\times \mathbb {Z} _{p}}
, where each factor corresponds to modular addition of values. Now, consider the function
f
:
:
Z
p
×
×
Z
p
→
→
G
;
f
(
a
,
b
)
=
g
a
x
−
−
b
.
{\displaystyle f\colon \mathbb {Z} _{p}\times \mathbb {Z} _{p}\to G\;;\;f(a,b)=g^{a}x^{-b}.}
This gives us an abelianhidden subgroup problem, wheref{\displaystyle f}corresponds to agroup homomorphism. Thekernelcorresponds to the multiples of(r,1){\displaystyle (r,1)}. So, if we can find the kernel, we can findr{\displaystyle r}. A quantum algorithm for solving this problem exists. This algorithm is, like the factor-finding algorithm, due to Peter Shor and both are implemented by creating a superposition through using Hadamard gates, followed by implementingf{\displaystyle f}as a quantum transform, followed finally by a quantum Fourier transform.[3]Due to this, the quantum algorithm for computing the discrete logarithm is also occasionally referred to as "Shor's Algorithm."

This gives us an abelian
hidden subgroup problem
, where
f
{\displaystyle f}
corresponds to a
group homomorphism
. The
kernel
corresponds to the multiples of
(
r
,
1
)
{\displaystyle (r,1)}
. So, if we can find the kernel, we can find
r
{\displaystyle r}
. A quantum algorithm for solving this problem exists. This algorithm is, like the factor-finding algorithm, due to Peter Shor and both are implemented by creating a superposition through using Hadamard gates, followed by implementing
f
{\displaystyle f}
as a quantum transform, followed finally by a quantum Fourier transform.
[
3
]
Due to this, the quantum algorithm for computing the discrete logarithm is also occasionally referred to as "Shor's Algorithm."
The order-finding problem can also be viewed as a hidden subgroup problem.[3]To see this, consider the group of integers under addition, and for a givena∈Z{\displaystyle a\in \mathbb {Z} }such that:ar=1{\displaystyle a^{r}=1}, the function

The order-finding problem can also be viewed as a hidden subgroup problem.
[
3
]
To see this, consider the group of integers under addition, and for a given
a
∈
∈
Z
{\displaystyle a\in \mathbb {Z} }
such that:
a
r
=
1
{\displaystyle a^{r}=1}
, the function
f
:
:
Z
→
→
Z
;
f
(
x
)
=
a
x
,
f
(
x
+
r
)
=
f
(
x
)
.
{\displaystyle f\colon \mathbb {Z} \to \mathbb {Z} \;;\;f(x)=a^{x},\;f(x+r)=f(x).}
For any finite abelian groupG{\displaystyle G}, a quantum algorithm exists for solving the hidden subgroup forG{\displaystyle G}in polynomial time.[3]

For any finite abelian group
G
{\displaystyle G}
, a quantum algorithm exists for solving the hidden subgroup for
G
{\displaystyle G}
in polynomial time.
[
3
]

## See also

See also
[
edit
]
- GEECM, a factorization algorithm said to be "often much faster than Shor's"[24]
GEECM
, a factorization algorithm said to be "often much faster than Shor's"
[
24
]
- Grover's algorithm
Grover's algorithm

## References

References
[
edit
]
- ^Shor, P.W. (1994). "Algorithms for quantum computation: Discrete logarithms and factoring".Proceedings 35th Annual Symposium on Foundations of Computer Science. pp.124–134.doi:10.1109/sfcs.1994.365700.ISBN978-0-8186-6580-6.
^
Shor, P.W. (1994). "Algorithms for quantum computation: Discrete logarithms and factoring".
Proceedings 35th Annual Symposium on Foundations of Computer Science
. pp.
124–
134.
doi
:
10.1109/sfcs.1994.365700
.
ISBN
978-0-8186-6580-6
.
- ^abcdShor, Peter W. (October 1997). "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer".SIAM Journal on Computing.26(5):1484–1509.arXiv:quant-ph/9508027.doi:10.1137/S0097539795293172.S2CID2337707.
^
a
b
c
d
Shor, Peter W. (October 1997). "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer".
SIAM Journal on Computing
.
26
(5):
1484–
1509.
arXiv
:
quant-ph/9508027
.
doi
:
10.1137/S0097539795293172
.
S2CID
2337707
.
- ^abcdeNielsen, Michael A.; Chuang, Isaac L. (9 December 2010).Quantum Computation and Quantum Information(PDF)(7th ed.). Cambridge University Press.ISBN978-1-107-00217-3.Archived(PDF)from the original on 2019-07-11. Retrieved24 April2022.
^
a
b
c
d
e
Nielsen, Michael A.; Chuang, Isaac L. (9 December 2010).
Quantum Computation and Quantum Information
(PDF)
(7th ed.). Cambridge University Press.
ISBN
978-1-107-00217-3
.
Archived
(PDF)
from the original on 2019-07-11
. Retrieved
24 April
2022
.
- ^Gidney, Craig; Ekerå, Martin (2021). "How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits".Quantum.5433.arXiv:1905.09749.Bibcode:2021Quant...5..433G.doi:10.22331/q-2021-04-15-433.S2CID162183806.
^
Gidney, Craig; Ekerå, Martin (2021). "How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits".
Quantum
.
5
433.
arXiv
:
1905.09749
.
Bibcode
:
2021Quant...5..433G
.
doi
:
10.22331/q-2021-04-15-433
.
S2CID
162183806
.
- ^See alsopseudo-polynomial time.
^
See also
pseudo-polynomial time
.
- ^Beckman, David; Chari, Amalavoyal N.; Devabhaktuni, Srikrishna;Preskill, John(August 1996). "Efficient networks for quantum factoring".Physical Review A.54(2):1034–1063.arXiv:quant-ph/9602016.Bibcode:1996PhRvA..54.1034B.doi:10.1103/physreva.54.1034.PMID9913575.
^
Beckman, David; Chari, Amalavoyal N.; Devabhaktuni, Srikrishna;
Preskill, John
(August 1996). "Efficient networks for quantum factoring".
Physical Review A
.
54
(2):
1034–
1063.
arXiv
:
quant-ph/9602016
.
Bibcode
:
1996PhRvA..54.1034B
.
doi
:
10.1103/physreva.54.1034
.
PMID
9913575
.
- ^Harvey, David; van der Hoeven, Joris (March 2021)."Integer multiplication in time O (n log n)"(PDF).Annals of Mathematics.193(2).doi:10.4007/annals.2021.193.2.4.
^
Harvey, David; van der Hoeven, Joris (March 2021).
"Integer multiplication in time O (n log n)"
(PDF)
.
Annals of Mathematics
.
193
(2).
doi
:
10.4007/annals.2021.193.2.4
.
- ^"Number Field Sieve".wolfram.com. Retrieved23 October2015.
^
"Number Field Sieve"
.
wolfram.com
. Retrieved
23 October
2015
.
- ^Roetteler, Martin; Naehrig, Michael;Svore, Krysta M.;Lauter, Kristin E.(2017). "Quantum resource estimates for computing elliptic curve discrete logarithms". In Takagi, Tsuyoshi; Peyrin, Thomas (eds.).Advances in Cryptology – ASIACRYPT 2017 – 23rd International Conference on the Theory and Applications of Cryptology and Information Security, Hong Kong, China, December 3–7, 2017, Proceedings, Part II. Lecture Notes in Computer Science. Vol. 10625. Springer. pp.241–270.arXiv:1706.06752.doi:10.1007/978-3-319-70697-9_9.ISBN978-3-319-70696-2.
^
Roetteler, Martin; Naehrig, Michael;
Svore, Krysta M.
;
Lauter, Kristin E.
(2017). "Quantum resource estimates for computing elliptic curve discrete logarithms". In Takagi, Tsuyoshi; Peyrin, Thomas (eds.).
Advances in Cryptology – ASIACRYPT 2017 – 23rd International Conference on the Theory and Applications of Cryptology and Information Security, Hong Kong, China, December 3–7, 2017, Proceedings, Part II
. Lecture Notes in Computer Science. Vol. 10625. Springer. pp.
241–
270.
arXiv
:
1706.06752
.
doi
:
10.1007/978-3-319-70697-9_9
.
ISBN
978-3-319-70696-2
.
- ^Vandersypen, Lieven M. K.; Steffen, Matthias; Breyta, Gregory; Yannoni, Costantino S.; Sherwood, Mark H.; Chuang, Isaac L. (December 2001). "Experimental realization of Shor's quantum factoring algorithm using nuclear magnetic resonance".Nature.414(6866):883–887.arXiv:quant-ph/0112176.Bibcode:2001Natur.414..883V.doi:10.1038/414883a.PMID11780055.
^
Vandersypen, Lieven M. K.; Steffen, Matthias; Breyta, Gregory; Yannoni, Costantino S.; Sherwood, Mark H.; Chuang, Isaac L. (December 2001). "Experimental realization of Shor's quantum factoring algorithm using nuclear magnetic resonance".
Nature
.
414
(6866):
883–
887.
arXiv
:
quant-ph/0112176
.
Bibcode
:
2001Natur.414..883V
.
doi
:
10.1038/414883a
.
PMID
11780055
.
- ^Lu, Chao-Yang; Browne, Daniel E.; Yang, Tao; Pan, Jian-Wei (19 December 2007). "Demonstration of a Compiled Version of Shor's Quantum Factoring Algorithm Using Photonic Qubits".Physical Review Letters.99(25) 250504.arXiv:0705.1684.Bibcode:2007PhRvL..99y0504L.doi:10.1103/PhysRevLett.99.250504.PMID18233508.
^
Lu, Chao-Yang; Browne, Daniel E.; Yang, Tao; Pan, Jian-Wei (19 December 2007). "Demonstration of a Compiled Version of Shor's Quantum Factoring Algorithm Using Photonic Qubits".
Physical Review Letters
.
99
(25) 250504.
arXiv
:
0705.1684
.
Bibcode
:
2007PhRvL..99y0504L
.
doi
:
10.1103/PhysRevLett.99.250504
.
PMID
18233508
.
- ^Lanyon, B. P.; Weinhold, T. J.; Langford, N. K.; Barbieri, M.; James, D. F. V.; Gilchrist, A.; White, A. G. (19 December 2007). "Experimental Demonstration of a Compiled Version of Shor's Algorithm with Quantum Entanglement".Physical Review Letters.99(25) 250505.arXiv:0705.1398.Bibcode:2007PhRvL..99y0505L.doi:10.1103/PhysRevLett.99.250505.PMID18233509.
^
Lanyon, B. P.; Weinhold, T. J.; Langford, N. K.; Barbieri, M.; James, D. F. V.; Gilchrist, A.; White, A. G. (19 December 2007). "Experimental Demonstration of a Compiled Version of Shor's Algorithm with Quantum Entanglement".
Physical Review Letters
.
99
(25) 250505.
arXiv
:
0705.1398
.
Bibcode
:
2007PhRvL..99y0505L
.
doi
:
10.1103/PhysRevLett.99.250505
.
PMID
18233509
.
- ^Lucero, Erik; Barends, Rami; Chen, Yu; Kelly, Julian; Mariantoni, Matteo; Megrant, Anthony; O'Malley, Peter; Sank, Daniel; Vainsencher, Amit; Wenner, James; White, Ted; Yin, Yi; Cleland, Andrew N.; Martinis, John M. (2012). "Computing prime factors with a Josephson phase qubit quantum processor".Nature Physics.8(10): 719.arXiv:1202.5707.Bibcode:2012NatPh...8..719L.doi:10.1038/nphys2385.S2CID44055700.
^
Lucero, Erik; Barends, Rami; Chen, Yu; Kelly, Julian; Mariantoni, Matteo; Megrant, Anthony; O'Malley, Peter; Sank, Daniel; Vainsencher, Amit; Wenner, James; White, Ted; Yin, Yi; Cleland, Andrew N.; Martinis, John M. (2012). "Computing prime factors with a Josephson phase qubit quantum processor".
Nature Physics
.
8
(10): 719.
arXiv
:
1202.5707
.
Bibcode
:
2012NatPh...8..719L
.
doi
:
10.1038/nphys2385
.
S2CID
44055700
.
- ^Martín-López, Enrique; Laing, Anthony; Lawson, Thomas; Alvarez, Roberto; Zhou, Xiao-Qi; O'Brien, Jeremy L. (12 October 2012). "Experimental realization of Shor's quantum factoring algorithm using qubit recycling".Nature Photonics.6(11):773–776.arXiv:1111.4147.Bibcode:2012NaPho...6..773M.doi:10.1038/nphoton.2012.259.S2CID46546101.
^
Martín-López, Enrique; Laing, Anthony; Lawson, Thomas; Alvarez, Roberto; Zhou, Xiao-Qi; O'Brien, Jeremy L. (12 October 2012). "Experimental realization of Shor's quantum factoring algorithm using qubit recycling".
Nature Photonics
.
6
(11):
773–
776.
arXiv
:
1111.4147
.
Bibcode
:
2012NaPho...6..773M
.
doi
:
10.1038/nphoton.2012.259
.
S2CID
46546101
.
- ^Monz, Thomas; Nigg, Daniel; Martinez, Esteban A.; Brandl, Matthias F.; Schindler, Philipp; Rines, Richard; Wang, Shannon X.; Chuang, Isaac L.; Blatt, Rainer (4 March 2016). "Realization of a scalable Shor algorithm".Science.351(6277):1068–1070.arXiv:1507.08852.Bibcode:2016Sci...351.1068M.doi:10.1126/science.aad9480.PMID26941315.S2CID17426142.
^
Monz, Thomas; Nigg, Daniel; Martinez, Esteban A.; Brandl, Matthias F.; Schindler, Philipp; Rines, Richard; Wang, Shannon X.; Chuang, Isaac L.; Blatt, Rainer (4 March 2016). "Realization of a scalable Shor algorithm".
Science
.
351
(6277):
1068–
1070.
arXiv
:
1507.08852
.
Bibcode
:
2016Sci...351.1068M
.
doi
:
10.1126/science.aad9480
.
PMID
26941315
.
S2CID
17426142
.
- ^Smolin, John A.; Smith, Graeme; Vargo, Alexander (July 2013). "Oversimplifying quantum factoring".Nature.499(7457):163–165.arXiv:1301.7007.Bibcode:2013Natur.499..163S.doi:10.1038/nature12290.PMID23846653.
^
Smolin, John A.; Smith, Graeme; Vargo, Alexander (July 2013). "Oversimplifying quantum factoring".
Nature
.
499
(7457):
163–
165.
arXiv
:
1301.7007
.
Bibcode
:
2013Natur.499..163S
.
doi
:
10.1038/nature12290
.
PMID
23846653
.
- ^Bernstein, Daniel (1998). "Detecting perfect powers in essentially linear time".Mathematics of Computation.67(223):1253–1283.doi:10.1090/S0025-5718-98-00952-1.
^
Bernstein, Daniel (1998). "Detecting perfect powers in essentially linear time".
Mathematics of Computation
.
67
(223):
1253–
1283.
doi
:
10.1090/S0025-5718-98-00952-1
.
- ^For example, computing the firstlog2⁡(N){\displaystyle \log _{2}(N)}roots ofN{\displaystyle N}, e.g., with theNewton methodand checking each integer result for primality (AKS primality test).
^
For example, computing the first
log
2
⁡
⁡
(
N
)
{\displaystyle \log _{2}(N)}
roots of
N
{\displaystyle N}
, e.g., with the
Newton method
and checking each integer result for primality (
AKS primality test
).
- ^Ekerå, Martin (June 2021)."On completely factoring any integer efficiently in a single run of an order-finding algorithm".Quantum Information Processing.20(6) 205.arXiv:2007.10044.Bibcode:2021QuIP...20..205E.doi:10.1007/s11128-021-03069-1.
^
Ekerå, Martin (June 2021).
"On completely factoring any integer efficiently in a single run of an order-finding algorithm"
.
Quantum Information Processing
.
20
(6) 205.
arXiv
:
2007.10044
.
Bibcode
:
2021QuIP...20..205E
.
doi
:
10.1007/s11128-021-03069-1
.
- ^Kitaev, A. Yu (1995). "Quantum measurements and the Abelian Stabilizer Problem".arXiv:quant-ph/9511026.
^
Kitaev, A. Yu (1995). "Quantum measurements and the Abelian Stabilizer Problem".
arXiv
:
quant-ph/9511026
.
- ^Ekerå, Martin (May 2024)."On the Success Probability of Quantum Order Finding".ACM Transactions on Quantum Computing.5(2):1–40.arXiv:2201.07791.doi:10.1145/3655026.
^
Ekerå, Martin (May 2024).
"On the Success Probability of Quantum Order Finding"
.
ACM Transactions on Quantum Computing
.
5
(2):
1–
40.
arXiv
:
2201.07791
.
doi
:
10.1145/3655026
.
- ^Markov, Igor L.; Saeedi, Mehdi (2012). "Constant-Optimized Quantum Circuits for Modular Multiplication and Exponentiation".Quantum Information and Computation.12(5–6):361–394.arXiv:1202.6614.Bibcode:2012arXiv1202.6614M.doi:10.26421/QIC12.5-6-1.S2CID16595181.
^
Markov, Igor L.; Saeedi, Mehdi (2012). "Constant-Optimized Quantum Circuits for Modular Multiplication and Exponentiation".
Quantum Information and Computation
.
12
(
5–
6):
361–
394.
arXiv
:
1202.6614
.
Bibcode
:
2012arXiv1202.6614M
.
doi
:
10.26421/QIC12.5-6-1
.
S2CID
16595181
.
- ^Markov, Igor L.; Saeedi, Mehdi (2013). "Faster Quantum Number Factoring via Circuit Synthesis".Phys. Rev. A.87(1) 012310.arXiv:1301.3210.Bibcode:2013PhRvA..87a2310M.doi:10.1103/PhysRevA.87.012310.S2CID2246117.
^
Markov, Igor L.; Saeedi, Mehdi (2013). "Faster Quantum Number Factoring via Circuit Synthesis".
Phys. Rev. A
.
87
(1) 012310.
arXiv
:
1301.3210
.
Bibcode
:
2013PhRvA..87a2310M
.
doi
:
10.1103/PhysRevA.87.012310
.
S2CID
2246117
.
- ^Bernstein, Daniel J.; Heninger, Nadia; Lou, Paul; Valenta, Luke (2017). "Post-quantum RSA".Post-Quantum Cryptography. Lecture Notes in Computer Science. Vol. 10346. pp.311–329.doi:10.1007/978-3-319-59879-6_18.ISBN978-3-319-59878-9.
^
Bernstein, Daniel J.; Heninger, Nadia; Lou, Paul; Valenta, Luke (2017). "Post-quantum RSA".
Post-Quantum Cryptography
. Lecture Notes in Computer Science. Vol. 10346. pp.
311–
329.
doi
:
10.1007/978-3-319-59879-6_18
.
ISBN
978-3-319-59878-9
.

## Further reading

Further reading
[
edit
]
- Nielsen, Michael A.; Chuang, Isaac L. (2010).Quantum Computation and Quantum Information: 10th Anniversary Edition. Cambridge University Press.ISBN978-1-107-00217-3.
Nielsen, Michael A.; Chuang, Isaac L. (2010).
Quantum Computation and Quantum Information: 10th Anniversary Edition
. Cambridge University Press.
ISBN
978-1-107-00217-3
.
- Kaye, Phillip; Laflamme, Raymond; Mosca, Michele (2006).An Introduction to Quantum Computing.doi:10.1093/oso/9780198570004.001.0001.ISBN978-0-19-857000-4.
Kaye, Phillip; Laflamme, Raymond; Mosca, Michele (2006).
An Introduction to Quantum Computing
.
doi
:
10.1093/oso/9780198570004.001.0001
.
ISBN
978-0-19-857000-4
.
- "Explanation for the man in the street"byScott Aaronson, "approved" by Peter Shor. (Shor wrote "Great article, Scott! That's the best job of explaining quantum computing to the man on the street that I've seen."). An alternate metaphor for the QFT was presented inone of the comments. Scott Aaronson suggests the following 12 references as further reading (out of "the 10105000quantum algorithm tutorials that are already on the web."):
"Explanation for the man in the street"
by
Scott Aaronson
, "
approved
" by Peter Shor. (Shor wrote "Great article, Scott! That's the best job of explaining quantum computing to the man on the street that I've seen."). An alternate metaphor for the QFT was presented in
one of the comments
. Scott Aaronson suggests the following 12 references as further reading (out of "the 10
10
5000
quantum algorithm tutorials that are already on the web."):
- Shor, Peter W. (1997), "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer",SIAM J. Comput.,26(5):1484–1509,arXiv:quant-ph/9508027v2,Bibcode:1999SIAMR..41..303S,doi:10.1137/S0036144598347011. Revised version of the original paper by Peter Shor ("28 pages, LaTeX. This is an expanded version of a paper that appeared in the Proceedings of the 35th Annual Symposium on Foundations of Computer Science, Santa Fe, New Mexico, November 20--22, 1994. Minor revisions made January, 1996").
Shor, Peter W. (1997), "Polynomial-Time Algorithms for Prime Factorization and Discrete Logarithms on a Quantum Computer",
SIAM J. Comput.
,
26
(5):
1484–
1509,
arXiv
:
quant-ph/9508027v2
,
Bibcode
:
1999SIAMR..41..303S
,
doi
:
10.1137/S0036144598347011
. Revised version of the original paper by Peter Shor ("28 pages, LaTeX. This is an expanded version of a paper that appeared in the Proceedings of the 35th Annual Symposium on Foundations of Computer Science, Santa Fe, New Mexico, November 20--22, 1994. Minor revisions made January, 1996").
- Quantum Computing and Shor's Algorithm, Matthew Hayward'sQuantum Algorithms Page, 2005-02-17, imsa.edu, LaTeX2HTML version of the originalLaTeX document, also available asPDForpostscriptdocument.
Quantum Computing and Shor's Algorithm
, Matthew Hayward's
Quantum Algorithms Page
, 2005-02-17, imsa.edu, LaTeX2HTML version of the original
LaTeX document
, also available as
PDF
or
postscript
document.
- Quantum Computation and Shor's Factoring Algorithm, Ronald de Wolf, CWI and University of Amsterdam, January 12, 1999, 9 page postscript document.
Quantum Computation and Shor's Factoring Algorithm
, Ronald de Wolf, CWI and University of Amsterdam, January 12, 1999, 9 page postscript document.
- Shor's Factoring Algorithm, Notes from Lecture 9 of Berkeley CS 294–2, dated 4 Oct 2004, 7 page postscript document.
Shor's Factoring Algorithm
, Notes from Lecture 9 of Berkeley CS 294–2, dated 4 Oct 2004, 7 page postscript document.
- Chapter 6 Quantum ComputationArchived2020-04-30 at theWayback Machine, 91 page postscript document, Caltech, Preskill, PH229.
Chapter 6 Quantum Computation
Archived
2020-04-30 at the
Wayback Machine
, 91 page postscript document, Caltech, Preskill, PH229.
- Quantum computation: a tutorialbySamuel L. Braunstein.
Quantum computation: a tutorial
by
Samuel L. Braunstein
.
- The Quantum States of Shor's Algorithm, by Neal Young, Last modified: Tue May 21 11:47:38 1996.
The Quantum States of Shor's Algorithm
, by Neal Young, Last modified: Tue May 21 11:47:38 1996.
- III. Breaking RSA Encryption with a Quantum Computer: Shor's Factoring Algorithm, Lecture notes on Quantum computation, Cornell University, Physics 481–681, CS 483; Spring, 2006 by N. David Mermin. Last revised 2006-03-28, 30 page PDF document.
III. Breaking RSA Encryption with a Quantum Computer: Shor's Factoring Algorithm
, Lecture notes on Quantum computation, Cornell University, Physics 481–681, CS 483; Spring, 2006 by N. David Mermin. Last revised 2006-03-28, 30 page PDF document.
- Lavor, C.; Manssur, L. R. U.; Portugal, R. (2003). "Shor's Algorithm for Factoring Large Integers".arXiv:quant-ph/0303175.
Lavor, C.; Manssur, L. R. U.; Portugal, R. (2003). "Shor's Algorithm for Factoring Large Integers".
arXiv
:
quant-ph/0303175
.
- Lomonaco, Jr (2000). "Shor's Quantum Factoring Algorithm".arXiv:quant-ph/0010034.This paper is a written version of a one-hour lecture given on Peter Shor's quantum factoring algorithm. 22 pages.
Lomonaco, Jr (2000). "Shor's Quantum Factoring Algorithm".
arXiv
:
quant-ph/0010034
.
This paper is a written version of a one-hour lecture given on Peter Shor's quantum factoring algorithm. 22 pages.
- Chapter 20 Quantum Computation, fromComputational Complexity: A Modern Approach, Draft of a book: Dated January 2007, Sanjeev Arora and Boaz Barak, Princeton University. Published as Chapter 10 Quantum Computation of Sanjeev Arora, Boaz Barak, "Computational Complexity: A Modern Approach", Cambridge University Press, 2009,ISBN978-0-521-42426-4
Chapter 20 Quantum Computation
, from
Computational Complexity: A Modern Approach
, Draft of a book: Dated January 2007, Sanjeev Arora and Boaz Barak, Princeton University. Published as Chapter 10 Quantum Computation of Sanjeev Arora, Boaz Barak, "Computational Complexity: A Modern Approach", Cambridge University Press, 2009,
ISBN
978-0-521-42426-4
- A Step Toward Quantum Computing: Entangling 10 Billion Particles.Archived2011-01-20 at theWayback Machine, from "Discover Magazine", Dated January 19, 2011.
A Step Toward Quantum Computing: Entangling 10 Billion Particles
.
Archived
2011-01-20 at the
Wayback Machine
, from "Discover Magazine", Dated January 19, 2011.
- Josef Gruska -Quantum Computing Challengesalso inMathematics unlimited: 2001 and beyond, Editors Björn Engquist, Wilfried Schmid, Springer, 2001,ISBN978-3-540-66913-5
Josef Gruska -
Quantum Computing Challenges
also in
Mathematics unlimited: 2001 and beyond
, Editors Björn Engquist, Wilfried Schmid, Springer, 2001,
ISBN
978-3-540-66913-5

## External links

External links
[
edit
]
- Version 1.0.0 oflibquantum: contains a C language implementation of Shor's algorithm with their simulated quantum computer library, but the width variable in shor.c should be set to 1 to improve the runtime complexity.
Version 1.0.0 of
libquantum
: contains a C language implementation of Shor's algorithm with their simulated quantum computer library, but the width variable in shor.c should be set to 1 to improve the runtime complexity.
- PBS Infinite Seriescreated two videos explaining the math behind Shor's algorithm, "How to Break Cryptography" and "Hacking at Quantum Speed with Shor's Algorithm".
PBS Infinite Series
created two videos explaining the math behind Shor's algorithm, "
How to Break Cryptography
" and "
Hacking at Quantum Speed with Shor's Algorithm
".
- Complete implementation of Shor's algorithm with Classiq
Complete implementation of Shor's algorithm with Classiq

<!-- table omitted -->

- v
v
- t
t
- e
e
Quantum information science
General
- DiVincenzo's criteria
DiVincenzo's criteria
- NISQ era
NISQ era
- Quantum computingtimeline
Quantum computing
- timeline
timeline
- Quantum information
Quantum information
- Quantum programming
Quantum programming
- Quantum simulation
Quantum simulation
- Qubitphysical vs. logical
Qubit
- physical vs. logical
physical vs. logical
- Quantum processorscloud-based
Quantum processors
- cloud-based
cloud-based
Theorems
- Bell's
Bell's
- Eastin–Knill
Eastin–Knill
- Gleason's
Gleason's
- Gottesman–Knill
Gottesman–Knill
- Holevo's
Holevo's
- No-broadcasting
No-broadcasting
- No-cloning
No-cloning
- No-communication
No-communication
- No-deleting
No-deleting
- No-hiding
No-hiding
- No-teleportation
No-teleportation
- PBR
PBR
- Quantum speed limit
Quantum speed limit
- Threshold
Threshold
- Solovay–Kitaev
Solovay–Kitaev
- Schrödinger-HJW
Schrödinger-HJW
Quantum
communication
- Classical capacityentanglement-assistedquantum capacity
Classical capacity
- entanglement-assisted
entanglement-assisted
- quantum capacity
quantum capacity
- Entanglement distillation
Entanglement distillation
- Entanglement swapping
Entanglement swapping
- Monogamy of entanglement
Monogamy of entanglement
- LOCC
LOCC
- Quantum channelquantum network
Quantum channel
- quantum network
quantum network
- State purification
State purification
- Quantum teleportationquantum energy teleportationquantum gate teleportation
Quantum teleportation
- quantum energy teleportation
quantum energy teleportation
- quantum gate teleportation
quantum gate teleportation
- Superdense coding
Superdense coding

<!-- table omitted -->

Quantum cryptography
- Decoy state
Decoy state
- Hidden matching
Hidden matching
- Post-quantum cryptography
Post-quantum cryptography
- Quantum coin flipping
Quantum coin flipping
- Quantum money
Quantum money
- Quantum key distributionBB84SARG04other protocols
Quantum key distribution
- BB84
BB84
- SARG04
SARG04
- other protocols
other protocols
- Quantum secret sharing
Quantum secret sharing
Quantum algorithms
- Algorithmic cooling
Algorithmic cooling
- Amplitude amplification
Amplitude amplification
- Bernstein–Vazirani
Bernstein–Vazirani
- BHT
BHT
- Boson sampling
Boson sampling
- Deutsch–Jozsa
Deutsch–Jozsa
- Grover's
Grover's
- HHL
HHL
- Hidden subgroup
Hidden subgroup
- Magic state distillation
Magic state distillation
- Quantum annealing
Quantum annealing
- Quantum counting
Quantum counting
- Quantum Fourier transform
Quantum Fourier transform
- Quantum optimization
Quantum optimization
- Quantum phase estimation
Quantum phase estimation
- Shor's
Shor's
- Simon's
Simon's
- VQE
VQE
Quantum
complexity theory
- BQP
BQP
- DQC1
DQC1
- EQP
EQP
- QIP
QIP
- QMA
QMA
- PostBQP
PostBQP
Quantum
processor benchmarks
- Quantum supremacy
Quantum supremacy
- Quantum volume
Quantum volume
- QC scaling laws
QC scaling laws
- Randomized benchmarkingXEB
Randomized benchmarking
- XEB
XEB
- Relaxation timesT1T2
Relaxation times
- T1
T
1
- T2
T
2
Quantum
computing models
- Adiabatic quantum computation
Adiabatic quantum computation
- Continuous-variable quantum information
Continuous-variable quantum information
- One-way quantum computercluster state
One-way quantum computer
- cluster state
cluster state
- Quantum circuitquantum logic gate
Quantum circuit
- quantum logic gate
quantum logic gate
- Quantum machine learningquantum neural network
Quantum machine learning
- quantum neural network
quantum neural network
- Quantum Turing machine
Quantum Turing machine
- Topological quantum computer
Topological quantum computer
- Hamiltonian quantum computation
Hamiltonian quantum computation
Quantum
error correction
- Codes5 qubitCSSGKPquantum convolutionalstabilizerShorBacon–ShorSteaneToricgnu
Codes
- 5 qubit
5 qubit
- CSS
CSS
- GKP
GKP
- quantum convolutional
quantum convolutional
- stabilizer
stabilizer
- Shor
Shor
- Bacon–Shor
Bacon–Shor
- Steane
Steane
- Toric
Toric
- gnu
gnu
- Entanglement-assisted
Entanglement-assisted
Physical
implementations

<!-- table omitted -->

Quantum optics
- Cavity QED
Cavity QED
- Circuit QED
Circuit QED
- Linear optical QC
Linear optical QC
- KLM protocol
KLM protocol
Ultracold atoms
- Neutral atom QC
Neutral atom QC
- Trapped-ion QC
Trapped-ion QC
Spin
-based
- Kane QC
Kane QC
- Spin qubit QC
Spin qubit QC
- NV center
NV center
- NMR QC
NMR QC
Superconducting
- Charge qubit
Charge qubit
- Flux qubit
Flux qubit
- Phase qubit
Phase qubit
- Transmon
Transmon
Quantum
programming
- OpenQASM–Qiskit–IBM QX
OpenQASM
–
Qiskit
–
IBM QX
- Quil–Forest/Rigetti QCS
Quil
–
Forest/Rigetti QCS
- Cirq
Cirq
- Q#
Q#
- libquantum
libquantum
- many others...
many others...
- Quantum information science
Quantum information science
- Quantum mechanics topics
Quantum mechanics topics

<!-- table omitted -->

- v
v
- t
t
- e
e
Number-theoretic
algorithms
Primality tests
- AKS
AKS
- APR
APR
- Baillie–PSW
Baillie–PSW
- Elliptic curve
Elliptic curve
- Pocklington
Pocklington
- Fermat
Fermat
- Lucas
Lucas
- Lucas–Lehmer
Lucas–Lehmer
- Lucas–Lehmer–Riesel
Lucas–Lehmer–Riesel
- Proth's theorem
Proth's theorem
- Pépin's
Pépin's
- Quadratic Frobenius
Quadratic Frobenius
- Solovay–Strassen
Solovay–Strassen
- Miller–Rabin
Miller–Rabin
Prime-generating
- Sieve of Atkin
Sieve of Atkin
- Sieve of Eratosthenes
Sieve of Eratosthenes
- Sieve of Pritchard
Sieve of Pritchard
- Sieve of Sundaram
Sieve of Sundaram
- Wheel factorization
Wheel factorization
Integer factorization
- Continued fraction (CFRAC)
Continued fraction (CFRAC)
- Dixon's
Dixon's
- Lenstra elliptic curve (ECM)
Lenstra elliptic curve (ECM)
- Euler's
Euler's
- Pollard's rho
Pollard's rho
- p− 1
p
− 1
- p+ 1
p
+ 1
- Quadratic sieve (QS)
Quadratic sieve (QS)
- General number field sieve (GNFS)
General number field sieve (GNFS)
- Special number field sieve (SNFS)
Special number field sieve (SNFS)
- Rational sieve
Rational sieve
- Fermat's
Fermat's
- Shanks's square forms
Shanks's square forms
- Trial division
Trial division
- Shor's
Shor's
Multiplication
- Ancient Egyptian
Ancient Egyptian
- Long
Long
- Karatsuba
Karatsuba
- Toom–Cook
Toom–Cook
- Schönhage–Strassen
Schönhage–Strassen
- Fürer's
Fürer's
Euclidean
division
- Binary
Binary
- Chunking
Chunking
- Fourier
Fourier
- Goldschmidt
Goldschmidt
- Newton-Raphson
Newton-Raphson
- Long
Long
- Short
Short
- SRT
SRT
Discrete logarithm
- Baby-step giant-step
Baby-step giant-step
- Pollard rho
Pollard rho
- Pollard kangaroo
Pollard kangaroo
- Pohlig–Hellman
Pohlig–Hellman
- Index calculus
Index calculus
- Function field sieve
Function field sieve
Greatest common divisor
- Binary
Binary
- Euclidean
Euclidean
- Extended Euclidean
Extended Euclidean
- Lehmer's
Lehmer's
Modular square root
- Cipolla
Cipolla
- Pocklington's
Pocklington's
- Tonelli–Shanks
Tonelli–Shanks
- Berlekamp
Berlekamp
Other algorithms
- Chakravala
Chakravala
- Cornacchia
Cornacchia
- Exponentiation by squaring
Exponentiation by squaring
- Integer square root
Integer square root
- Integer relation(LLL;KZ)
Integer relation
(
LLL
;
KZ
)
- Modular exponentiation
Modular exponentiation
- Montgomery reduction
Montgomery reduction
- Schoof
Schoof
- Trachtenberg system
Trachtenberg system
- Italicsindicate that algorithm is for numbers of special forms
Italics
indicate that algorithm is for numbers of special forms
NewPP limit report
Parsed by mw‐web.codfw.main‐9f67c7b4b‐vcsht
Cached time: 20260611173431
Cache expiry: 2592000
Cache expiry source: Module:Citation/CS1 (os.date(%Y))
Reduced expiry: false
Complications: [vary‐revision‐sha1, prevent‐selective‐update, show‐toc]
CPU time usage: 0.747 seconds
Real time usage: 0.926 seconds
Preprocessor visited node count: 3150/1000000
Revision size: 38580/2097152 bytes
Post‐expand include size: 125774/2097152 bytes
Template argument size: 2083/2097152 bytes
Highest expansion depth: 12/100
Expensive parser function count: 2/500
Unstrip recursion depth: 1/20
Unstrip post‐expand size: 133076/5000000 bytes
Lua time usage: 0.307/10.000 seconds
Lua memory usage: 5926305/52428800 bytes
Number of Wikibase entities loaded: 0/500
Transclusion expansion time report (%,ms,calls,template)
100.00%  471.485      1 -total
 46.77%  220.496      1 Template:Reflist
 19.89%   93.783      5 Template:Cite_book
 19.57%   92.273     16 Template:Cite_journal
 16.91%   79.742      4 Template:Navbox
 16.04%   75.649      1 Template:Quantum_computing
 15.25%   71.910      1 Template:Short_description
 10.25%   48.336      2 Template:Pagetype
  6.70%   31.575      1 Template:Citation_needed
  5.57%   26.269      1 Template:Fix
Render ID cdba0048-65bb-11f1-a255-01110d5c4c41
Saved in parser cache with key enwiki:pcache:42674:|#|:idhash:canonical and timestamp 20260611173431 and revision id 1355557542. Rendering was triggered because: page_view
Retrieved from "
https://en.wikipedia.org/w/index.php?title=Shor%27s_algorithm&oldid=1355557542
"
Categories
:
- Quantum algorithms
Quantum algorithms
- Integer factorization algorithms
Integer factorization algorithms
- Post-quantum cryptography
Post-quantum cryptography
Hidden categories:
- Articles with short description
Articles with short description
- Short description matches Wikidata
Short description matches Wikidata
- All articles with unsourced statements
All articles with unsourced statements
- Articles with unsourced statements from August 2023
Articles with unsourced statements from August 2023
- Webarchive template wayback links
Webarchive template wayback links