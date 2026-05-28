# Commercial Release Checklist

## Product

- [ ] Run the app on the supported Windows versions.
- [ ] Test camera startup with camera index `0` and fallback camera selection.
- [ ] Test cursor movement, click, drag, scroll mode, desktop gestures, zoom, and stop behavior.
- [ ] Test voice commands with the shipped default voice engine.
- [ ] Verify dangerous voice commands remain locked by default.
- [ ] Add onboarding images or a short gesture tutorial.
- [ ] Add support contact, version number, and crash-reporting policy.

## Packaging

- [ ] Create a clean virtual environment.
- [ ] Install `requirements-dev.txt`.
- [ ] Confirm the build Python has working Tcl/Tk and runtime voice dependencies.
- [ ] Run `python -m compileall .\src\hands_free_control`.
- [ ] Run `powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1`.
- [ ] Test the packaged app on a machine without the development environment.
- [ ] Code-sign the release build when distributing broadly.
- [ ] Scan the release archive/installer before publishing.

## Business

- [ ] Publish the beta as free access with advanced/custom gesture features enabled.
- [ ] Record supported hardware, OS versions, and known limitations.
- [ ] Prepare a demo video and screenshots.
- [ ] Prepare refund, support, privacy, and license pages.
- [ ] Decide whether future monetization belongs in a later release.
- [ ] Keep Microsoft Store and GitHub release notes clear that this beta has no login or payment requirement.

## Legal And Accessibility

- [ ] Audit third-party licenses and notices.
- [ ] Match privacy disclosures to the actual camera/audio/voice behavior.
- [ ] Get legal review for your EULA, privacy policy, and sales terms if needed.
- [ ] Test keyboard accessibility for the desktop UI.
