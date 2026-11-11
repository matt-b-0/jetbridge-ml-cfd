# Presentation materials

Use this page as the entry point during the presentation. It is readable directly on GitHub.

- [Download the PowerPoint](Jet_Bridge_Presentation.pptx?raw=true) — six main slides with timed speaker notes. Fourteen optional backup slides are hidden during the slideshow.
- [Five-minute tutorial and questions](PRESENTATION_TUTORIAL.md).
- [Short source-code guide matched to the submitted report](../html/REPORT_CODE_GUIDE.md).
- [Exact submitted report PDF](../report/MMA3001_Jet_Bridge_FinalSubmission.pdf).
- [Tests explained line by line](TEST_WALKTHROUGH.md).
- [Speaker notes extracted from the deck](SPEAKER_NOTES.md).
- [The six core checks, including SVR leakage](../../tests/test_core.py).
- [Optional inner-scaling and other regression checks](../../tests/extended/test_four_workstreams.py).
- [Repository setup and reproduction](../../README.md).

The default test run is now **six cases in one file**, all passing. The wider regressions are optional for the presentation and remain in tests/extended. The full WSL collection still reports **128 passed, 1 skipped**; GitHub CI and the full demo quality gate retain that collection. Ruff passed. Scientific results are unchanged.

## HTML pages

GitHub's file viewer displays HTML source rather than running the page. To use the interactive tutorial, API documentation and readable test report, choose **Code → Download ZIP**, extract it, and open `docs/presentation/index.html`. All required pages are included and work offline. No Python or OpenFOAM installation is needed to read them. Running the numerical workflows requires the documented environment.

The local tutorial links the complete test source catalogue and current API. Two Tk-only module references are explicitly generated from source; they are not evidence of successful native execution.
The starting HTML now focuses on the submitted report and six relevant functions. The full API and extended tests are optional background. The deck's backup metric example is now in tests/test_core.py; use the current walkthrough for test locations.

## Main slides — browser fallback

Use these images if PowerPoint is unavailable. Each image is rendered from the packaged deck; editable slides and notes remain in the PPTX.

### 1. Jet bridge airflow

![Slide 1: Jet bridge airflow](slides/slide-01.png)

### 2. Experimental data and geometry

![Slide 2: Experimental data and geometry](slides/slide-02.png)

### 3. Interpolation and regression

![Slide 3: Interpolation and regression](slides/slide-03.png)

### 4. Prediction tests at withheld locations

![Slide 4: Prediction tests at withheld locations](slides/slide-04.png)

### 5. RBF has the lowest aggregate error

![Slide 5: RBF has the lowest aggregate error](slides/slide-05.png)

### 6. Limitations and AI reflection

![Slide 6: Limitations and AI reflection](slides/slide-06.png)

## Backup slides

- [7. CFD setup and initial conditions](slides/slide-07.png)
- [8. CFD overpredicts speed at all 12 sensors](slides/slide-08.png)
- [9. Repository, documentation and tests](slides/slide-09.png)
- [10. Backup  Libraries and their roles](slides/slide-10.png)
- [11. Backup  Reconstructing a CFD field](slides/slide-11.png)
- [12. Backup  Numerical stability and accuracy](slides/slide-12.png)
- [13. Backup  Sources and scope](slides/slide-13.png)
- [14. Alternative B  Size of the CFD overprediction](slides/slide-14.png)
- [15. Alternative C  Height profiles and temporal variation](slides/slide-15.png)
- [16. Alternative D  A simpler parity comparison](slides/slide-16.png)
- [17. Backup  Rubric evidence](slides/slide-17.png)
- [18. Backup  A test with a known answer](slides/slide-18.png)
- [19. Backup  Preventing test-data leakage](slides/slide-19.png)
- [20. Backup  Accuracy, robustness and computational cost](slides/slide-20.png)
