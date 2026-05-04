# Midlife — A Life-Strategy Model

The implementation of this model is the [pathwise](https://github.com/buwilliams/pathwise) app. This document defines the model. It does not draw a conclusion about what any specific midlifer should do.

You are somewhere between your late thirties and mid forties. You have built a life — a career, perhaps a partnership, perhaps children, a home, friendships, a body that is starting to talk back, savings, debts, opinions, scars. You are not deciding *whether* to be an adult. You are deciding what the second half is for. The decisions in front of you are large: change careers, start the business, go back to school, move, end the marriage, repair the marriage, adopt, take the sabbatical, get the dog, finally write the book. They feel different from the decisions at twenty because the cost of being wrong is higher and the cost of standing still is also higher.

The purpose of this model is not to prove the one correct answer. The purpose is to make the important factors explicit so you (or whoever is helping you) can use conjecture and criticism to evaluate possible paths.

The document has three main sections. Section 1 states the core conjecture. Section 2 formalizes it. Section 3 walks through the formalization in detail.

---

## 1. Conjecture

Time is your most valuable resource, and you have less of it than you did at twenty. It is finite, and it is spent whether or not you choose where it goes. A good life is one where time is directed at enjoyment.

Enjoyment is not the absence of difficulty. Hardship pursued toward an outcome you want is a good use of time. Hardship endured for an outcome you don't want is poor use of time. The goal modifies the difficulty from a good to a bad use of time.

The lived experience along the way is most of life. A path that ends well but spends years in misery is not the same as a path that ends equally well and is good to live through. The journey is what you live. Destinations are milestones along the journey.

Two things are different at midlife from earlier seasons. First, you have already built considerable momentum — career, money, skills, relationships, identity. The work is rarely to *create* momentum from zero; it is to *redirect* what is already moving toward something more aligned with who you have become. Second, the body of evidence about yourself is much larger. You know what drains you, what energizes you, what you tolerate well, what corrodes you over years. The model assumes that signal is real and trustworthy.

Emotions in this season are not noise. Persistent restlessness, dread on Sunday nights, a creative practice that has gone quiet, a sense of going through motions that no longer fit — these are evidence that current alignment has drifted, not character flaws to be willed away. The conjecture treats them as load-bearing inputs to the model rather than as friction to be overcome.

The conjecture is that the best path is one that creates **momentum** in a redirected sense: each step moves your life-state toward something more desirable, not merely something survivable, and uses the capacity you have already built rather than wishing it away.

That momentum must be adjustable, enjoyable to live through, digestible, and — distinctively at midlife — *brave enough to act on what you actually know*.

- **Adjustable**: the path is not chosen once. It is revised at each stage as new information arrives. An adjustable path requires that each step remain reversible enough to actually redirect. An irreversible decision shrinks future options regardless of whether it was good at the time. At midlife the adjustability bar is higher: irreversible decisions (a divorce, a sold business, a degree completed at fifty) sit on a horizon that is shorter than at twenty.
- **Enjoyable**: the path is judged by the lived experience across stages, not only by where it ends. At midlife the years are not interchangeable; the felt quality of this decade and the next is most of what you will recall.
- **Digestible**: the helper's role is to wrap the complexity of scarcity tradeoffs and path dependency in a presentation that can be acted on. The formalization below is the mental work of doing the heavy lifting alongside someone whose attention is divided across a job, a household, and several other people.
- **Brave**: at midlife the fail mode is not chaos but inertia. The model deliberately treats long stretches of stable but misaligned life-states as a failure, not a baseline. Standing still in a life that does not fit costs as much as a wrong move and offers nothing in return.

---

## 2. Formalized Model

### 2.1 State

$$
L = \{V, T, A, K, W\}
$$

$$
V = \{i_1, i_2, i_3, i_4, e, g, \beta\}
$$

$$
T = \{p, b, q\}
$$

$$
A = \{c, \sigma, d, r, y, \gamma\}
$$

$$
K = \{k, \tau, \mu, \rho, \delta\}
$$

$$
W = \{\phi, \psi, \zeta, \eta, \nu\}
$$

| Symbol | Meaning |
|---|---|
| $L$ | Life-state |
| $V$ | Values |
| $T$ | Time |
| $A$ | Assets (including income) |
| $K$ | Education / capability |
| $W$ | Health |
| $i_1$ | Mobility / agency over location |
| $i_2$ | Financial independence |
| $i_3$ | Residential / domestic alignment |
| $i_4$ | Decision independence (control over schedule, work, direction) |
| $e$ | Enjoyable life experience |
| $g$ | Goal progress (felt sense of moving toward something that matters) |
| $\beta$ | Stability / emotional safety |
| $p$ | Productive hours per week |
| $b$ | Buffer hours |
| $q$ | Quality of time / energy |
| $c$ | Monthly cash flow |
| $\sigma$ | Savings (incl. retirement, investments) |
| $d$ | Debt / liabilities |
| $r$ | Risk buffer / emergency fund |
| $y$ | Income |
| $\gamma$ | Income growth rate |
| $k$ | Capability / education path |
| $\tau$ | Time required for $k$ |
| $\mu$ | Money required for $k$ |
| $\rho$ | Completion / payoff risk for $k$ |
| $\delta$ | Technology trajectory of $k$ |
| $\phi$ | Physical health |
| $\psi$ | Mental health |
| $\zeta$ | Fitness practice (movement, food, sleep) |
| $\eta$ | Net emotional impact (signed) |
| $\nu$ | Relational quality (partner, friends, kids, community, family of origin) |

Subscripts: $x_s$ denotes $x$ in scenario $s$; $x_j$ denotes $x$ at stage $j$ of a path. Thresholds ($r_{min}$, $\phi_{min}$, $y_{min}$, $H$, $R_{min}$, etc.) are person-specific parameters.

Because time is finite and the most valuable resource — and noticeably scarcer at midlife than at twenty — it enters the model in three places: as the state variables in $T = \{p, b, q\}$, as stage durations $d_j$ weighting path momentum (§2.5), and as a horizon budget $H$ that bounds the total stage durations a path may spend. A typical midlife horizon is shorter than the teen one (commonly five to ten years rather than the open-ended runway of eighteen).

### 2.2 Cross-Variable Relationships

Capability's effects on time, assets, and projected income:

$$
p_{actual} = p_{baseline} - \tau_{weekly} \quad \text{during training}
$$

$$
\sigma_{after} = \sigma_{before} - \mu
$$

$$
E[\Delta y] = (1 - \rho) \cdot \Delta y_{\text{if complete}}
$$

$$
\hat{y}(L_s, H) = y_s \cdot (1 + \gamma_s)^H \cdot (1 + \delta_s)^H
$$

Emotional comparison between alternatives:

$$
\text{a choice becomes more attractive as } \eta(\text{this}) - \eta(\text{alternative}) \text{ rises}
$$

At midlife the emotional differential is especially load-bearing: many candidate paths produce nearly identical financial life-states and differ primarily in $\eta$ and $\nu$. The model does not penalize the user for taking that signal seriously.

### 2.3 Viable and Desirable

$$
L_{viable} = \{L : c \geq 0 \land r \geq r_{min} \land p \geq p_{min} \land b \geq b_{min} \land q \geq q_{min} \land \phi \geq \phi_{min} \land \psi \geq \psi_{min} \land \nu \geq \nu_{min}\}
$$

$$
L_{desirable} = L_{viable} \cap \{L : i_1 \geq i_{1,min} \land i_2 \geq i_{2,min} \land i_3 \geq i_{3,min} \land i_4 \geq i_{4,min} \land e \geq e_{min} \land g \geq g_{min} \land \beta \geq \beta_{min} \land y \geq y_{min} \land \sigma \geq d \land \hat{y}(L, H) \geq y_{min} \land \zeta \geq \zeta_{min} \land \eta \geq \eta_{min}\}
$$

$$
S_{viable} = \{s \in S : L_s \in L_{viable}\}, \quad S_{desirable} = \{s \in S : L_s \in L_{desirable}\}
$$

$$
S_{desirable} \subseteq S_{viable} \subseteq S
$$

A status-quo midlife is frequently $L_{viable}$ — the bills are paid, the body has not collapsed, the household functions — without being $L_{desirable}$. When $\eta < \eta_{min}$ or $g < g_{min}$ persistently, the current life-state is filtered out of desirable. The model is explicit that "we are getting by" is not the same as "this is a life worth wanting."

### 2.4 Adjustable

The path objective is applied iteratively. At each stage $j$, re-optimize over the paths still reachable from $L_j$:

$$
P^*_j = \arg\max_{P \in \mathcal{P}_j} Momentum(P)
$$

subject to the constraints in §2.5. Take $s_{j+1}$ as the first step of $P^*_j$. Observe $L_{j+1}$. Re-optimize. The model is a policy, not a fixed plan. As stages elapse, the remaining horizon shrinks; each re-optimization is bounded by $H - \sum_{k<j} d_k$, not the full $H$.

For the path to remain adjustable, individual decisions must stay reversible enough that future redirection is possible. Define how recoverable a decision is:

$$
R(s_j) = 1 - \frac{w_\lambda \lambda_j + w_\xi \xi_j + w_\Delta \Delta_j}{w_\lambda + w_\xi + w_\Delta}
$$

Where $\lambda_j, \xi_j, \Delta_j \in [0, 1]$ measure lock-in duration (as a fraction of $H$), exit cost (as a fraction of $\sigma$), and state disruption (fraction of $L$ materially altered). $w_\lambda, w_\xi, w_\Delta$ are person-specific weights. $R(s_j) \in [0, 1]$. The path objective requires $R(s_j) \geq R_{min}$ for each large decision.

Recoverability has a different texture at midlife than in earlier seasons. Some decisions that read as recoverable on paper (a job change, a move, a new business) carry larger $\Delta$ because the existing state has more components — partner career, kids' school, parents' proximity, professional identity. Conversely, some decisions that read as catastrophic (ending a misaligned partnership, leaving a high-paying job that is destroying $\psi$) score better than fear suggests once $\Delta$ is computed honestly against the cost of staying.

### 2.5 Momentum and Path Objective

$$
Momentum(L) = w_{qe} \cdot q \cdot e \;+\; \sum_{x \in components(L)} w_x \cdot x
$$

Where $components(L)$ ranges over the scored scalar sub-components of $V$, $T$, $A$, and $W$: $i_1, i_2, i_3, i_4, e, g, \beta, p, b, q, c, \sigma, r, y, \gamma, \phi, \psi, \zeta, \eta, \nu$. ($K$'s sub-components and $d$ are tracked but not directly scored.) The leading $q \cdot e$ term operationalizes "time directed at enjoyment"; the additive sum of $g$ and $\eta$ operationalizes "the goal modifies the difficulty." See §3.5.

Single-scenario optimum:

$$
s^* = \arg\max_{s \in S_{desirable}} Momentum(s)
$$

Path: $P = (s_0, s_1, \dots, s_n)$. Path momentum sums life-state quality across stages, weighted by stage duration $d_j$:

$$
Momentum(P) = \sum_{j=0}^{n} d_j \cdot Momentum(L_j)
$$

Path objective:

$$
P^* = \arg\max_{P \in \mathcal{P}} Momentum(P)
$$

subject to:

$$
L_n \in L_{desirable}, \quad L_j \in L_{viable} \;\forall j, \quad R(s_j) \geq R_{min} \;\forall \text{ large decisions } j
$$

and the horizon budget:

$$
\sum_{j=0}^{n} d_j \leq H
$$

A long stretch of viable-but-not-desirable life-state is not a free pass. It still consumes the horizon budget. At midlife this is the central mechanism: the model penalizes spending two or three of your remaining decade-blocks in a state of mere viability when a redirected path produces a desirable state in the same time.

---

## 3. Explanation

This section walks through Section 2 in order. Each subsection explains the reasoning behind a piece of the formalization: why it exists, why the choices in it were made, and what it captures from the conjecture.

### 3.1 State

Why model life as a state? Because the decisions you face are not isolated. Changing careers changes income, identity, schedule, household labor, retirement plans, and the way your kids see what is possible. Ending a partnership changes housing, money, time, parenting, friendships, and grief. A choice that improves one thing can quietly damage another. To compare candidate decisions honestly, the model needs a snapshot wide enough to be useful. No model captures everything. The goal is enough scope to surface the load-bearing tradeoffs without becoming unwieldy.

Why these five dimensions and not four or seven? Each can move without dragging the others with it. You can be financially comfortable but exhausted, or healthy but lonely, or skilled but stagnant in a job that uses none of it. Collapsing two dimensions into one would hide a tradeoff you actually face. The five chosen here are a working compromise between coverage and simplicity. If a needed dimension turns out to be missing, §3.6 lists that as a falsifiability trigger.

A life-state $L$ has five top-level dimensions: values ($V$), time ($T$), assets ($A$), capability ($K$), and health ($W$). Reasoning about midlife decisions requires reasoning about all of them.

#### Values ($V$)

Why values as a separate dimension? Because what you have is not the same as what you want, and at midlife the gap between the two is often the live problem. Two paths can leave you in identical financial and physical states with very different feelings about whether you are living the life you want. Values are the dimension that captures whether your situation matches what you actually care about *now*, which is rarely identical to what you were optimizing for at twenty-five.

Seven sub-components: four independence types plus enjoyable life experience ($e$), goal progress ($g$), and emotional safety ($\beta$).

The independence sub-types are reinterpreted for midlife. $i_1$ (mobility) is less about owning a car and more about freedom to be where you want to be — geographic flexibility, remote work, ability to travel without crisis. $i_2$ (financial) is freedom from coercion by your finances: not net worth, but the capacity to make non-financial choices. $i_3$ (residential / domestic) is whether your home and household configuration support the life you want, including the partnership inside it. $i_4$ (decision) is control over your schedule, your work, your direction; this is often the one that has eroded silently across years.

$g$ — goal progress — is felt, not measured. A midlifer who has accumulated objective accomplishments while losing the sense that any of it is leading anywhere meaningful has high $\sigma$ and low $g$. The model treats this as real.

$\beta$ — stability — is emotional safety and a sense that the floor under you is solid. Midlife introduces a tension here: stability can mean security, or it can mean stuckness. The viable filter requires $\beta \geq \beta_{min}$; the desirable filter does not require maximum $\beta$, since at this season some redirection requires temporary dips in stability that pay back.

Net worth is not in $V$. It is captured by $\sigma$ and $d$ in $A$, with the desirable filter requiring $\sigma_s \geq d_s$.

#### Time ($T$)

Why split time into three? Because counting available hours is not enough. At midlife the count is often dominated by obligations — work, kids, parents, household — and the question of whether the *remaining* hours are usable is the live one. Hours that are exhausted, scattered, or all spoken for in advance behave very differently from rested hours that can actually build a life.

Three sub-components: count ($p$), buffer ($b$), and quality ($q$).

A useful distinction: $p_{theoretical} \neq p_{actual}$. A plan can work on paper but fail if the remaining hours are tired, scattered, or emotionally overloaded. Many midlife life-states have non-trivial $p$ on paper and very low $p_{actual}$ once parenting, household, caregiving, and emotional load are deducted.

Time is the most valuable resource in the model, and the one most distinctively constrained at this season. It enters in three places: as the state variables in $T$, as stage durations $d_j$ that weight path momentum, and as a horizon budget $H$ that bounds the total time a path may spend.

#### Assets ($A$)

Why bundle income and assets together? Because they cannot be reasoned about separately, and at midlife the relationship between them is often distorted: high income with high household burn produces fragility; lower income with low overhead produces resilience. Cash flow is the difference between income and outflow. Savings is what cash flow accumulates. Splitting these across separate top-level dimensions would force the model to constantly re-couple them.

Six sub-components: monthly cash flow ($c$), savings ($\sigma$), debt ($d$), risk buffer ($r$), income ($y$), and growth rate ($\gamma$).

At midlife, $\sigma$ frequently includes retirement accounts and home equity that are not liquid. The model treats them as part of $\sigma$ for the desirability filter (net-worth $\sigma \geq d$) but separates liquidity into $r$, the months of overhead the *available* buffer covers. A household with $750{,}000 in retirement and a $5{,}000 emergency fund has high $\sigma$ and low $r$, and the model scores it as such.

A plan becomes financially fragile when $c < 0$ or $r < r_{min}$. A plan that meets those floors but produces $y < y_{min}$ is viable without being desirable: it can survive without yet supporting the life you want. $y_{min}$ is a desirable-state threshold, not a survival threshold.

A useful conjecture for this season: financial independence ($i_2$) becomes desirable when income is high enough — and burn low enough — that you can change directions without the change being vetoed by money.

#### Capability ($K$)

Why capability as its own dimension? Because at midlife it is the main non-monetary lever you have on direction. Health, time, and values are things you already have and modify. New capability is the thing you invest in now to change what is possible in five and ten years. Unlike at eighteen, you also already have a stack of accumulated capability that can be redeployed without retraining; the model treats redeployment of existing $K$ as the cheapest available move.

Five sub-components: a path ($k$), training time ($\tau$), training money ($\mu$), completion risk ($\rho$), and technology trajectory ($\delta$).

Capability here covers any path that builds skill or credential, formal or informal: a degree or certificate; an apprenticeship into a craft; a cohort program; a long-arc self-study; mentorship; an MBA or executive program; a sabbatical reframed as immersion in a new field. The model treats them as one category because what matters is the resulting capability, not the venue.

$\delta$ (technology trajectory) reflects that the $K \rightarrow y$ relationship is not stable across time. People create new knowledge, knowledge produces new technology, and technology reshapes which capabilities the market pays for. $\delta$ is signed: negative if exposed to displacement by emerging technology, near zero if tech-neutral over the relevant horizon, positive if amplified.

At midlife, $\delta$ on the *current* career path is often the unspoken question driving restlessness. A path that pays well today but has a strongly negative $\delta$ over a five-to-ten-year horizon is a fragile platform regardless of current income.

#### Health ($W$)

Why model health holistically? Because the dimensions of well-being are not interchangeable, and at midlife each one is at risk in distinctive ways. A plan can succeed financially while the body decays. Another can sustain physical health while loneliness grows. Treating health as a single number would let one of these masquerade as the other. The five sub-components let the model see each dimension on its own.

Five sub-components: physical ($\phi$), mental ($\psi$), fitness ($\zeta$), emotional impact ($\eta$), and relational quality ($\nu$).

$\phi$ and $\psi$ at midlife are no longer abstractions that compound silently — they are starting to send bills. Sleep that was negotiable at twenty-five is a hard constraint at forty. Anxiety left untreated has compounded for fifteen years. A path that produces strong income but degrades $\phi$ or $\psi$ is a path that is paying interest forever, often at the worst time.

$\zeta$ is the practice, not the state: what you actually do day to day around movement, food, and sleep. State ($\phi$) follows practice ($\zeta$) over time. A plan that leaves no time or energy for $\zeta$ will eventually erode $\phi$.

$\eta$ is signed: positive when a choice feels net good day to day, negative when it does not. At midlife, persistent negative $\eta$ in a structurally stable life is the central diagnostic signal. The model does not treat it as a character flaw to be willed away; it treats it as evidence about alignment.

| Choice | Possible emotional impact at midlife |
|---|---|
| Stay in current career | Continuity, mastery, and security, against drift, identity erosion, and Sunday-night dread |
| Change careers | Renewed engagement, alignment, and growth, against income hit, status loss, and starting again |
| Start a business | Agency, ownership, and meaning, against financial risk, household stress, and social isolation |
| Return to school | Identity expansion, new community, against cost, time away from family, and uncertain payoff |
| Move (city or country) | Reset, novelty, possibility, against community loss, partner stress, and kid disruption |
| Repair a partnership | Depth, gratitude, and shared future, against grief work, vulnerability, and uncertainty |
| Leave a partnership | Relief, alignment, possibility, against loss, financial hit, and grief that lasts years |
| Have / adopt a child | Meaning, expansion of love, identity, against sleep loss, money, and decade-scale obligation |
| Take a sabbatical | Recovery, perspective, creativity, against income gap, career risk, and guilt |
| Get a pet | Daily affection, structure, meaning, against time, money, and a hard ending in 10–15 years |

$\nu$ at midlife is non-trivially fragile. Many midlife life-states show low $\nu$ not because the person did anything wrong but because the structures that created social connection earlier — schools, college, early-career offices, neighbourhood through young children — have aged out. Many plans look efficient on paper but quietly damage $\nu$. Long hours leave no time for friends. A move can sever a community before a new one forms. Some damage is reversible. Some is not.

$\phi$, $\psi$, and $\nu$ are floors in the viable filter. $\zeta$ and $\eta$ contribute to momentum but are not hard floors: a plan can briefly skip exercise or feel hard without becoming nonviable. They become floors implicitly when sustained low values destroy $\phi$ or $\psi$.

> No plan is a good plan if it ruins your body, your mind, or your closeness to the people who matter. Feeling bad for a stretch is survivable. Staying broken is not.

### 3.2 Cross-Variable Relationships

Why model relationships between dimensions at all? Because the dimensions are not actually independent. Capability does cost time and money. Field-level technology shifts do affect income. Without these connections, the model is a list of categories rather than a working system that can estimate what a candidate decision will produce. The estimates are approximations, not predictions; they exist to support comparison, not to forecast.

Capability's sub-components connect to time, assets, and projected income through four formal relationships:

- $\tau$ (training time) reduces $p$ during the training period. While training is in progress, $p_{actual} = p_{baseline} - \tau_{weekly}$. After training ends, $p$ returns to baseline.
- $\mu$ (training money) subtracts from $\sigma$ at training start, or amortizes across the training horizon.
- $\rho$ (completion risk) discounts the expected post-training income gain. A 30 percent risk of not completing a program discounts the expected $\Delta y$ by 30 percent. At midlife, $\rho$ for a self-paced credential when also working full-time and parenting can be substantial; the model takes that seriously.
- $\hat{y}(L_s, H)$ projects current income forward over the planning horizon, combining personal growth $\gamma$ and field-level technology trajectory $\delta$.

Emotional comparison between alternatives uses the difference of net emotional impacts: a choice becomes more attractive as $\eta(\text{this}) - \eta(\text{alternative}) \geq 0$.

### 3.3 Viable and Desirable

Why two filters and not one? Because survival is not the same as flourishing, and at midlife the difference is the live question. A plan can be technically possible but actually awful to live. A status-quo midlife is often viable indefinitely; the model is built to refuse the inference that "viable indefinitely" implies "we should keep doing this."

Two filters separate plans by quality.

$L_{viable}$ contains life-states that survive: nonnegative cash flow, sufficient risk buffer, all three time dimensions above their floors, and physical, mental, and relational health above their floors. Failing any of these means the plan is nonviable, regardless of how attractive it looks elsewhere.

$L_{desirable}$ is a strict subset of $L_{viable}$. A desirable life-state additionally has each independence type meeting its minimum, named values ($e$, $g$, $\beta$) above their floors, current and projected income meeting $y_{min}$, positive net worth ($\sigma \geq d$), and fitness and emotional impact above their floors.

The distinction matters because a plan that feels exciting but creates a brittle life is filtered out as nonviable before any momentum comparison happens. Among viable plans, only desirable ones produce a life worth wanting.

### 3.4 Adjustable

Why a policy rather than a fixed plan? Because the future cannot be predicted in detail, and at midlife you have firsthand evidence of how poorly any plan committed at twenty-five has aged. New information will arrive (a job offer, a diagnosis, a child's needs, a market shift, a parent's decline) and a plan committed years in advance will be out of date by the time it gets executed. Treating the model as a policy means you use it again at each stage, with whatever you have actually learned.

For the path to remain adjustable, individual decisions must stay reversible enough that future redirection is possible. State-level resilience is handled by the viable-state floors. How recoverable each decision is determines whether the path stays adjustable.

$R(s_j) \in [0, 1]$ measures how recoverable decision $s_j$ is, computed from three dimensions. $\lambda_j$ is lock-in duration as a fraction of the planning horizon. $\xi_j$ is exit cost as a fraction of savings. $\Delta_j$ is state disruption: roughly the fraction of $L$'s sub-components materially changed by the decision.

Examples (midlife-flavored):

| Decision | $\lambda$ | $\xi$ | $\Delta$ | $R$ |
|---|---:|---:|---:|---:|
| Take a 4-week course | 0.05 | 0.02 | 0.10 | 0.94 |
| Start a side business while keeping the day job | 0.20 | 0.10 | 0.20 | 0.83 |
| Take a 6-month sabbatical | 0.10 | 0.20 | 0.30 | 0.80 |
| Sell the home and move to a lower-COL city | 0.40 | 0.30 | 0.60 | 0.57 |
| Quit to launch a business full-time | 0.40 | 0.40 | 0.50 | 0.57 |
| Return to a 2-year graduate program | 0.40 | 0.40 | 0.40 | 0.60 |
| Initiate a divorce | 0.50 | 0.40 | 0.80 | 0.43 |
| Have a third child | 0.80 | 0.30 | 0.70 | 0.40 |

These $R$ values are starting points, not verdicts. The model deliberately surfaces low-$R$ decisions early so they can be examined honestly rather than slid into.

> Prefer decisions you can step back from. Irreversible decisions need more evidence than reversible ones — and at midlife, the body of evidence about yourself is exactly what makes a few of them defensible.

### 3.5 Momentum and Path Objective

Why reduce the life-state to a single number? Because you need to compare options, and comparison requires reduction. Many things matter, and they matter differently. Momentum is the weighted sum that lets the model say one path scores higher than another without dropping any of the components that built the score. The score is a comparison aid, not a verdict.

The leading $w_{qe} \cdot q \cdot e$ term operationalizes "time directed at enjoyment." At midlife the asymmetry is sharp: hours spent on grinding obligations score low even when objectively productive, because $e$ is low. Hours spent in flow on something that matters score high even when sparser, because $q$ and $e$ are jointly high.

The additive sum of $g$ and $\eta$ implements "the goal modifies the difficulty." Hardship pursued toward a wanted outcome appears as positive $g$ outweighing negative $\eta$ in the sum. Hardship endured without progress appears as zero or negative $g$ alongside negative $\eta$, netting negative contribution.

The weights are person-specific importances. At midlife the suggested calibration tilts toward $\eta$, $\psi$, $\nu$, and $\beta$ — the emotional, mental-health, relational, and stability axes — because these are the ones that most often quietly fail in viable-but-not-desirable midlife states.

A typical fail mode the model is built to surface: a path that is structurally fine, financially sound, and produces a flat or slowly-eroding $\eta$ over many stages. Path momentum is the duration-weighted sum, so years of low-$\eta$ life-state weigh as much as the income they produce. The model treats this as a real cost, not a rounding error.

#### Horizon budget

$\sum_{j=0}^{n} d_j \leq H$ is what makes time the binding resource. A path cannot extend beyond the planning horizon $H$. Longer stages crowd out shorter ones. Scenarios that move toward desirable life-states quickly leave more horizon for further refinement; scenarios that linger consume the budget without progressing.

At midlife this is the central mechanism. The remaining horizon is shorter than at twenty. Spending three years getting back to the start of a redirected path that would have required two is a real cost. The model is built to make that visible rather than to ignore it.

### 3.6 Falsifiability

The model is itself a conjecture and should be revisable. Conditions that should trigger revision:

- A scenario produces high momentum but feels emotionally wrong. (A value is missing or mis-weighted.)
- A scenario looks viable on paper but fails repeatedly in practice. (A constraint is uncosted.)
- Your stated values shift in a stable, considered way. ($V$ needs updating — and at midlife this is normal, not a failure.)
- A variable in $L$ turns out to be redundant, or a needed variable is missing.
- The weights in $Momentum$ produce rankings that contradict considered judgment across many scenarios.
- The horizon-projected income $\hat{y}$ produces predictions that are repeatedly wrong by large margins.

> The model is a tool for thinking, not a verdict. When it stops fitting reality, change the model.
