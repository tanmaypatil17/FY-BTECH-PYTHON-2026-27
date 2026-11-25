# MITIn AI Candidate Search

An AI-assisted candidate search feature for the MITIn recruiter dashboard. Recruiters can describe the type of student they are looking for using natural language, including skills, academic branch, and CGPA criteria. The backend attempts to use Google Gemini 2.5 Flash and falls back to a local Python matching engine if Gemini is unavailable.

> **Integration pack:** These files are feature additions extracted from a larger MITIn Django project. They are not a complete standalone Django application and should be merged into the corresponding files in the main repository.

## Project flow

1. A recruiter enters a search prompt in the dashboard.
2. The browser sends the prompt as JSON to `POST /api/ai-search/`.
3. Django retrieves eligible `StudentProfile` records and prepares candidate data.
4. If `GEMINI_API_KEY` is configured, the backend sends the prompt and candidate data to Gemini.
5. If Gemini is not configured or the API request fails, the local Python evaluator processes the query.
6. The backend returns JSON containing a summary, ranked matches, scores, reasons, and the engine source.
7. The dashboard matches returned PRNs to existing candidate cards and displays the results.

## Files

| File | Purpose | Integration location |
|---|---|---|
| `01_views_py_additions.py` | Candidate matching logic and Django API view | Merge required imports into `profiles/views.py`; add both functions and the API-key configuration |
| `02_urls_py_route.txt` | Django URL route | Add the line inside `urlpatterns` in `mitin_core/urls.py` |
| `03_recruiter_dashboard_html_insertions.html` | Search panel, match badge, and reason element | Insert the panel into the recruiter dashboard template; add badge and reason elements to each existing candidate card |
| `04_recruiter_dashboard_js_insertions.js` | Browser-side search and result rendering | Add inside the existing dashboard script scope after `allCards` is defined |
| `.env.example` | Environment variable placeholder | Use as a reference; do not commit a real API key |

## Integration instructions

### 1. Backend

In `profiles/views.py`:

- Merge the imports from `01_views_py_additions.py` with the existing imports. Avoid duplicating imports already present.
- Add the `GEMINI_API_KEY` environment-variable configuration.
- Add `evaluate_candidates_python_ai()` and `ai_candidate_search()` to the module.
- Confirm that `StudentProfile` is the correct model and that its field names match the fields used by this feature.

Do not replace the entire existing `views.py`; it may contain views used by other parts of MITIn.

### 2. URL route

Add this route inside the existing `urlpatterns` list in `mitin_core/urls.py`:

```python
path('api/ai-search/', views.ai_candidate_search, name='api_ai_candidate_search'),
```

Ensure the file already imports the relevant `views` module. Keep all existing URL patterns.

### 3. Dashboard HTML

Insert the search panel from `03_recruiter_dashboard_html_insertions.html` into the recruiter pool/dashboard template.

For each existing candidate card:

- Add `data-prn="{{ student.prn }}"` to its article/container element.
- Place the `.ai-match-badge` element inside the card's top metadata row.
- Place the `.ai-reason-box` paragraph inside the card body.
- Ensure the page contains `candidates-grid`, `candidate-count-pill`, `no-ai-matches`, `empty-reset-btn`, and every other element ID referenced by the JavaScript.

The supplied HTML is a fragment, not a replacement for the complete dashboard template or candidate-card loop.

### 4. Dashboard JavaScript

Add `04_recruiter_dashboard_js_insertions.js` inside the existing dashboard script or DOM-ready scope, after `allCards` has been defined.

Do not declare another `const allCards` in the same scope. The JavaScript expects the HTML elements and IDs described above to exist.

### 5. Gemini API key

Set the key as an environment variable. Never place a real API key in source code or commit it to GitHub.

PowerShell example for the current terminal session:

```powershell
$env:GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
python manage.py runserver
```

The Django server must be started from the same terminal session in which the variable is set.

For deployments, configure `GEMINI_API_KEY` through the hosting provider's environment-variable/secret settings.

## Search behaviour

### Gemini mode

When a key is configured, the backend sends the recruiter query and candidate profile data to the Gemini `gemini-2.5-flash` generate-content endpoint. The expected response is JSON with:

- `ai_summary`: a short explanation of the search.
- `matches`: candidate PRNs, match scores, and reasons.

### Local fallback mode

If no key is configured or the Gemini request fails, the Python fallback:

- Recognizes common CGPA range, minimum, and maximum expressions.
- Recognizes several branch names and abbreviations.
- Extracts likely keywords from the recruiter prompt.
- Scores candidates using the detected branch, keyword matches, and CGPA criteria.

The fallback score is heuristic, not a statistically validated measure. Its weighting is based on the applicable categories in the implementation: branch (35), skills (55), and CGPA (25), normalized over the categories used and capped at 99.

## Important limitations and review notes

- The source implementation's Gemini condition contained a self-comparison that always evaluated to false. It has been corrected in this package to `if GEMINI_API_KEY:` so the Gemini request can run when a key is configured.
- The local fallback's docstring in the original source referred to internship availability, but the matching logic does not currently filter by `open_to_internships`.
- A plain CGPA query such as `CGPA 7` is treated by the fallback as a range from 6.5 to 7.99, not exact equality.
- Gemini's returned PRNs and scores are used by the original implementation without independently validating every result against the database and query constraints. Add server-side validation before relying on the output in production.
- The view uses `@csrf_exempt`. This does not authenticate the recruiter or authorize access to candidate data. Add appropriate authentication, recruiter authorization, rate limiting, and CSRF protection before production deployment.
- Candidate profile information is sent to the external Gemini API when Gemini mode is enabled. Review privacy, consent, and organizational data-handling requirements before enabling it.
- The endpoint and Gemini model availability have not been tested against the live MITIn deployment as part of preparing this integration pack.

## Before merging

- [ ] Confirm model names and field names against the main MITIn repository.
- [ ] Confirm `allCards` and all required dashboard element IDs.
- [ ] Configure `GEMINI_API_KEY` outside source control.
- [ ] Add authentication and recruiter authorization to the API endpoint.
- [ ] Validate AI-returned PRNs and scores on the server.
- [ ] Test both Gemini mode and local fallback mode.
- [ ] Test empty queries, invalid requests, and API failures.

## License

No license is specified in this integration pack. Add the license selected by the main MITIn project before publishing it as an independently reusable repository.
