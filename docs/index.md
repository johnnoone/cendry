# Cendry

A Firestore ODM for Python. Typed models, composable filters, sync and async.

---

| | |
|---|---|
| **[Tutorials](tutorials/index.md)** | Learn Cendry step by step. Start here if you're new. |
| **[How-To Guides](how-to/index.md)** | Practical recipes for common tasks. |
| **[Reference](reference/index.md)** | Technical details of every class and function. |
| **[Explanation](explanation/index.md)** | Understand the design and architecture. |

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
