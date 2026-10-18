# src/topics/__init__.py
"""
Configuration topics: what a lab teaches, as opposed to what a rule checks.

registry.py   which topics exist, which rule categories each owns, and how
              each is detected in a reference file
weights.py    how a lab's points are split between topics
<topic>.py    a grader for one topic (static_routes.py is the first)
"""
