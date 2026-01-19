# Interface folder

## Purpose

The `interface/` folder defines the entry points into the application. It is responsible for receiving input from the outside world, translating it into application-level requests, and returning responses in an appropriate format.

This layer contains no business logic. Its role is to adapt external protocols (HTTP, CLI, etc.) to the internal service and domain APIs.
