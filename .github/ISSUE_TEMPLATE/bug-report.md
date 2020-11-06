---
name: Bug report
about: Unexpected behavior? Tell us more
title: ''
labels: bug
assignees: ''

---

# Describe your issue

(Tell us what the problem is in a few word)

# Your environment

Please provide the following informations:
 - Current Inmanta version: 
 - Operating System: 
 - Python version:
 - PostgreSQL version:

Using Linux? You can replace the list by the output of the following command:  
echo " - $(inmanta --version)"; \
echo " - OS: $(source /etc/os-release; echo $PRETTY_NAME)"; \
echo " - Python version: $(python3 --version)"; \
echo " - PostreSQL version: $(psql --version)"

# Steps to reproduce

1. step 1
2. step 2
3. you get it...

# Expected behavior

(Tell us what you expected this list of steps to do)

# Actual behavior

(Tell us what actually happened)

# (Optional) You already found the solution to this problem?

(You can add detail about the resolution of this issue here)

# (Optional) Are you willing to contribute and try solving this issue?
 - [ ] Yes
