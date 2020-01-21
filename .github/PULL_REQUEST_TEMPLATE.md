## Breaking change
<!--
  If your PR contains a breaking change for existing users, it is important
  to tell them what breaks, how to make it work again and why we did this.
  This piece of text is published with the release notes, so it helps if you
  write it towards our users, not us.
  Note: Remove this section if this PR is NOT a breaking change.
-->


## Proposed change
<!-- 
    Describe the big picture of your changes here to communicate to the
    maintainers why we should accept this pull request. If it fixes a bug
    or resolves a feature request, be sure to link to that issue in the 
    additional information section.
-->


## Type of change
<!--
    What types of changes does your PR introduce to our documention/website?
    Put an `x` in the boxes that apply. You can also fill these out after
    creating the PR.
-->

- [ ] Bugfix (non-breaking change which fixes an issue)
- [ ] New integration (thank you!)
- [ ] New feature (which adds functionality to an existing integration)
- [ ] Breaking change (fix or feature that would cause existing functionality not to work as expected)
- [ ] Code quality improvements to existing code or addition of tests

## Example entry for `configuration.yaml`:
<!--
    Supplying a configuration snippet, makes it easier for a maintainer to test
    your PR. Furthermore, for new integrations, it gives an impression of how
    the configuration would look like.
    Note: Remove this section if this PR does not have an example entry.
-->

```yaml

```

## Additional information
<!--
    Details are important, and help maintainers processing your PR.
    Please be sure to fill out additional details, if applicable.
-->

- This PR fixes or closes issue: fixes #
- This PR is related to issue: 
- Link to documentation pull request: 

## Checklist
<!--
    Put an `x` in the boxes that apply. You can also fill these out after
    creating the PR. If you're unsure about any of them, don't hesitate to ask.
    We're here to help! This is simply a reminder of what we are going to look
    for before merging your code.
-->

- [ ] The code change is tested and works locally.
- [ ] Local tests pass. **Your PR cannot be merged unless tests pass**
- [ ] There is no commented out code in this PR.
- [ ] I have followed the [development checklist][dev-checklist]
- [ ] The code has been formatted using Black (`black --fast homeassistant tests`)
- [ ] Tests have been added to verify that the new code works.

If user exposed functionality or configuration variables are added/changed:

- [ ] Documentation added/updated in [home-assistant.io][docs-repository]

If the code communicates with devices, web services, or third-party tools:

- [ ] [_The manifest file_][manifest-docs] has all fields filled out correctly. Update and include derived files by running `python3 -m script.hassfest`.
- [ ] New or updated dependencies have been added to `requirements_all.txt` by running `python3 -m script.gen_requirements_all`.
- [ ] Untested files have been added to `.coveragerc`.

The integration reached or maintains the following Integration Quality Scale:
<!-- https://developers.home-assistant.io/docs/en/next/integration_quality_scale_index.html -->

- [ ] No score or internal
- [ ] 🥈 Silver
- [ ] 🥇 Gold
- [ ] 🏆 Platinum

[dev-checklist]: https://developers.home-assistant.io/docs/en/development_checklist.html
[manifest-docs]: https://developers.home-assistant.io/docs/en/creating_integration_manifest.html
[quality-scale]: https://developers.home-assistant.io/docs/en/next/integration_quality_scale_index.html
[docs-repository]: https://github.com/home-assistant/home-assistant.io
