# Workspace support in the Inmanta vs-code extension

* Status: accepted
* Deciders: [Sander, Hugo]
* Date: 2023-03-13

Technical Story: [Original ticket](https://github.com/inmanta/vscode-inmanta/issues/892)

## Context and Problem Statement

When working in a workspace, multiple Inmanta projects and/or modules can be opened at the same time.
Some official guidelines are provided [here](https://github.com/Microsoft/vscode/wiki/Adopting-Multi-Root-Workspace-APIs#single-language-server-or-server-per-folder)
to help guide the choice of having one language server for all the folders, or one language server per folder.

## Decision Drivers

* We want the functionalities offered by the Inmanta extension when working on a single project or module to work
seamlessly when working in a workspace.
* We want to make sure independent projects or modules are isolated from each other and don't pollute each other's
environments.

## Considered Options

1. one language server for all the folders
2. one language server per folder
3. one language server per venv

## Decision Outcome

Chosen option: option 2, because it is the best compromise between allowing isolation between folders when desired and
ease of implementation.

When a `.cf` file is opened, if the folder it belongs to is not already being managed by a language server, then we
prompt the user to select a venv for this folder and spin a language server up.

## Pros and Cons of the Options

### [option 1]

* Bad, because there is no isolation between folders, all dependencies would be installed in the same venv. This might
be a desired behaviour in some cases, but is not acceptable in most cases. The issue of incompatible requirements would
also arise.
* Good, because a single server is started.

### [option 2]

* Good, because there is isolation between folders as long as different venvs are selected.
* Good, because it still allows folders to share a venv if desired, by selecting the same venv.
* Good, because of ease of implementation: each language server is responsible for only one folder and doesn't need to
listen to changes to the workspace. The extension is the one responsible for listening to the changes to the workspace
and starting/stopping language servers as needed.
* Bad, because resource-hungry: one server is started per folder.


### [option 3]

* Good, because there is isolation between folders as long as different venvs are selected.
* Good, because less resource-hungry than option 2: one server is started per virtual environment.
* Bad, because harder to implement than option 2.
* Bad, because more resource-hungry than option 1: one server is started per virtual environment.

