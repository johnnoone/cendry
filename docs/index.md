# Cendry

A Firestore ODM for Python. Typed models, composable filters, sync and async.

---

<div class="grid cards" markdown>

-   :material-school:{ .lg .middle } **Tutorials**

    ---

    Learn Cendry step by step.

    [:octicons-arrow-right-24: First steps](tutorials/first-steps.md)

-   :material-directions:{ .lg .middle } **How-To Guides**

    ---

    Solve specific problems.

    [:octicons-arrow-right-24: How-to guides](how-to/index.md)

-   :material-book-open-variant:{ .lg .middle } **Reference**

    ---

    Technical details of every class and function.

    [:octicons-arrow-right-24: API reference](reference/index.md)

-   :material-lightbulb:{ .lg .middle } **Explanation**

    ---

    Understand the design and architecture.

    [:octicons-arrow-right-24: Explanation](explanation/index.md)

</div>

## Installation

```bash
pip install cendry
```

## Requirements

- Python >= 3.13
- Google Cloud project with Firestore enabled

## Quick look

```python
from cendry import Model, Field, Cendry

class City(Model, collection="cities"):
    name: Field[str]
    state: Field[str]
    population: Field[int]

with Cendry() as ctx:
    for city in ctx.select(City, City.state == "CA").limit(10):
        print(city.name, city.population)
```
