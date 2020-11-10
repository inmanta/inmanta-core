---
name: Bug report
about: Unexpected behavior? Tell us more
title: ''
labels: bug
assignees: ''

---

# Describe your issue

(Tell us what the problem is in a few words)

# Steps to reproduce

1. step 1
2. step 2
3. ...
4. result

# Expected behavior

(Tell us what you expected this list of steps to do)

# Work around (if any)

(You can add detail about the resolution of this issue here)

# Your environment

Please provide the following information:
 - Current Inmanta version: 
 - Operating System: 
 - Python version:
 - PostgreSQL version:

Using Linux? You can replace the list by the output of the following command:  
echo " - $(inmanta --version)"; \
echo " - OS: $(source /etc/os-release; echo $PRETTY_NAME)"; \
echo " - Python version: $(python3 --version)"; \
echo " - PostreSQL version: $(psql --version)"