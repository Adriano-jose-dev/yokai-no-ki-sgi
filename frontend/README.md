# YNKApp — SGI-YKR

<!-- Badge de status do CI (GitHub Actions).
     Substitua OWNER/REPO pelo caminho real do repositório no GitHub
     (ex.: yokai-dojo/sgi-ykr) para a badge apontar para o seu workflow. -->
[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)

Front-end Angular do **Sistema de Gestão Interna Yōkai no Ki Ryūha (SGI-YKR)**.
O back-end (API FastAPI) fica em [`YnkBD/`](YnkBD/); o guia de produção está em
[`../README_DEPLOY.md`](../README_DEPLOY.md).

This project was generated with [Angular CLI](https://github.com/angular/angular-cli) version 13.3.11.

## Integração Contínua (CI)

A cada `push` e `pull_request` na branch `main`, o workflow
[`.github/workflows/ci.yml`](.github/workflows/ci.yml) executa dois jobs:

- **Back-end**: Python 3.12, instala `YnkBD/requirements.txt` e roda `pytest`.
- **Front-end**: Node.js 16, `npm ci` e `npm run build` (build de produção).

## Development server

Run `ng serve` for a dev server. Navigate to `http://localhost:4200/`. The application will automatically reload if you change any of the source files.

## Code scaffolding

Run `ng generate component component-name` to generate a new component. You can also use `ng generate directive|pipe|service|class|guard|interface|enum|module`.

## Build

Run `ng build` to build the project. The build artifacts will be stored in the `dist/` directory.

## Running unit tests

Run `ng test` to execute the unit tests via [Karma](https://karma-runner.github.io).

## Running end-to-end tests

Run `ng e2e` to execute the end-to-end tests via a platform of your choice. To use this command, you need to first add a package that implements end-to-end testing capabilities.

## Further help

To get more help on the Angular CLI use `ng help` or go check out the [Angular CLI Overview and Command Reference](https://angular.io/cli) page.
