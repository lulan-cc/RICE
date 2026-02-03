# Dataset

## History ICE Issues
We have organized reports of two known ICE defects as a test dataset. You can collect historical ICE issues from the [Rust GitHub repository](https://github.com/rust-lang/rust/issues?q=is%3Aissue%20state%3Aopen%20label%3AC-bug%20label%3AI-ICE%20label%3AT-compiler) to expand the dataset, but please organize them according to the example format we provide:
```
## Trigger Code
<ICE-triggering code>

## Compiler Output
<compiler crash info>
```

## Adaptation Contexts
The program will automatically download the official compiler test suite during runtime to serve as the application's context environment, located in the `rust/tests/ui` directory.