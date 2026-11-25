import json
import os
import re
import traceback
import urllib.request
import urllib.error

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import StudentProfile
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def evaluate_candidates_python_ai(recruiter_query, candidates_list):
    q = recruiter_query.lower().strip()
    min_cgpa = None
    max_cgpa = None
    strict_less = False
    strict_greater = False
    between_m = re.search(r'(?:between|from)\s*(\d+(?:\.\d+)?)\s*(?:and|to|-)\s*(\d+(?:\.\d+)?)', q)
    if between_m:
        v1, v2 = float(between_m.group(1)), float(between_m.group(2))
        if v1 <= 10 and v2 <= 10:
            min_cgpa, max_cgpa = min(v1, v2), max(v1, v2)
    if max_cgpa is None:
        below_patterns = [
            r'(below|under|less\s+than|lower\s+than|max|maximum|upto|up\s+to|<=|<)\s*(?:cgpa|gpa|score|of|:)?\s*(\d+(?:\.\d+)?)',
            r'(?:cgpa|gpa|score)\s*(?:is\s*)?(below|under|less\s+than|lower\s+than|max|maximum|upto|<=|<)\s*(\d+(?:\.\d+)?)'
        ]
        for pat in below_patterns:
            m = re.search(pat, q)
            if m and float(m.group(2)) <= 10:
                op = m.group(1)
                max_cgpa = float(m.group(2))
                if op in ('below', 'under', '<') or 'less' in op or 'lower' in op:
                    strict_less = True
                break
    if min_cgpa is None:
        plus_m = re.search(r'(\d+(?:\.\d+)?)\s*\+', q)
        if plus_m and float(plus_m.group(1)) <= 10:
            min_cgpa = float(plus_m.group(1))
        else:
            above_patterns = [
                r'(above|over|more\s+than|greater\s+than|higher\s+than|min|minimum|at\s+least|least|>=|>)\s*(?:cgpa|gpa|score|of|:)?\s*(\d+(?:\.\d+)?)',
                r'(?:cgpa|gpa|score)\s*(?:is\s*)?(above|over|more\s+than|greater\s+than|min|minimum|>=|>)\s*(\d+(?:\.\d+)?)'
            ]
            for pat in above_patterns:
                m = re.search(pat, q)
                if m and float(m.group(2)) <= 10:
                    op = m.group(1)
                    min_cgpa = float(m.group(2))
                    if op in ('above', 'over', '>') or 'more' in op or 'greater' in op:
                        strict_greater = True
                    break
    if min_cgpa is None and max_cgpa is None:
        exact_m = re.search(r'(?:cgpa|gpa)\s*(?:of|is|=|:|around)?\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:cgpa|gpa)', q)
        if exact_m:
            val = float(exact_m.group(1) or exact_m.group(2))
            if val <= 10:
                min_cgpa = max(0.0, val - 0.5)
                max_cgpa = min(10.0, val + 0.99)
    branch_map = [
        ('AI & Data Science', 'ai & data science', ['ai-ds', 'aids', 'ai&ds', 'data science', 'artificial intelligence', 'ai']),
        ('Computer Science & Engineering', 'computer science', ['cse', 'cs', 'computer science', 'comp']),
        ('Information Technology', 'information technology', ['it', 'information technology', 'infotech']),
        ('Mechanical Engineering', 'mechanical', ['mech', 'mechanical']),
        ('Electronics & Telecom', 'electronics', ['entc', 'ece', 'electronics', 'telecom']),
    ]
    detected_branches = []
    for label, match_key, triggers in branch_map:
        for trig in triggers:
            if re.search(r'\b' + re.escape(trig) + r'\b', q):
                detected_branches.append((label, match_key))
                break
    stop_words = {
        'looking', 'lookng', 'lookin', 'lokking', 'searching', 'search', 'find', 'finding',
        'for', 'an', 'a', 'the', 'who', 'whom', 'whose', 'knows', 'know', 'knowing',
        'with', 'without', 'and', 'or', 'in', 'of', 'to', 'from', 'by', 'on', 'as', 'is', 'are',
        'student', 'students', 'studnt', 'graduate', 'graduates', 'candidate', 'candidates', 'canditate',
        'someone', 'somebody', 'person', 'people', 'profile', 'profiles', 'guy', 'girl',
        'good', 'great', 'best', 'strong', 'expert', 'proficient', 'at', 'skilled', 'experienced',
        'having', 'has', 'have', 'need', 'needs', 'want', 'wants', 'hire', 'hiring',
        'developer', 'developers', 'engineer', 'engineers', 'engineering', 'coder', 'programmer',
        'branch', 'department', 'dept', 'stream', 'cgpa', 'gpa', 'cpi', 'score', 'grade', 'marks', 'pointer',
        'above', 'over', 'minimum', 'min', 'least', 'greater', 'higher', 'more', 'than', 'top',
        'below', 'under', 'less', 'lower', 'maximum', 'max', 'upto', 'up', 'within', 'between', 'around',
        'equal', 'equals', 'exact', 'exactly', 'only', 'show', 'me', 'get', 'give', 'all', 'any', 'list',
        'mit', 'wpu', 'mitwpu', 'college', 'university', 'campus', 'year', 'class', 'batch',
        'ai-ds', 'aids', 'ai&ds', 'cse', 'cs', 'it', 'mech', 'entc', 'ece', 'ai'
    }
    raw_tokens = [
        w for w in re.sub(r'[^a-z0-9.#+\-]', ' ', re.sub(r'(\d+(?:\.\d+)?)\s*\+', ' ', q)).split()
        if len(w) > 1 and w not in stop_words and not w.replace('.', '', 1).isdigit()
    ]

    vocab = set()
    for c in candidates_list:
        text_blob = f"{c['full_name']} {c['branch']} {c['skills']} {c['bio']}".lower()
        for w in re.sub(r'[^a-z0-9.#+\-]', ' ', text_blob).split():
            if len(w) > 1:
                vocab.add(w)

    has_structural = (min_cgpa is not None or max_cgpa is not None or len(detected_branches) > 0)
    skill_keywords = []
    for tok in raw_tokens:
        if not has_structural or any((tok in vw or vw in tok) for vw in vocab):
            skill_keywords.append(tok)

    matches = []
    for c in candidates_list:
        cgpa = float(c.get('cgpa') or 0.0)
        if min_cgpa is not None:
            if strict_greater and cgpa <= min_cgpa:
                continue
            if not strict_greater and cgpa < min_cgpa:
                continue
        if max_cgpa is not None:
            if strict_less and cgpa >= max_cgpa:
                continue
            if not strict_less and cgpa > max_cgpa:
                continue

        branch_lower = (c.get('branch') or '').lower()
        skills_lower = (c.get('skills') or '').lower()
        bio_lower = (c.get('bio') or '').lower()
        name_lower = (c.get('full_name') or '').lower()
        full_text = f"{name_lower} {branch_lower} {skills_lower} {bio_lower}"

        score = 0.0
        max_possible = 0.0
        reasons = []

        if detected_branches:
            max_possible += 35.0
            if any(mk in branch_lower for _, mk in detected_branches):
                score += 35.0
                reasons.append(f"Branch: {c.get('branch')}")

        if skill_keywords:
            max_possible += 55.0
            pts = 55.0 / len(skill_keywords)
            matched_kws = []
            for kw in skill_keywords:
                if kw in skills_lower:
                    score += pts
                    matched_kws.append(kw)
                elif kw in full_text:
                    score += pts * 0.8
                    matched_kws.append(kw)
            if matched_kws:
                reasons.append(f"Matched: {', '.join(matched_kws)}")

        if min_cgpa is not None or max_cgpa is not None:
            max_possible += 25.0
            score += 25.0
            reasons.append(f"CGPA {cgpa:.2f} meets threshold")

        if max_possible == 0:
            max_possible = 100.0
            if q in full_text:
                score = 92.0

        pct = min(99, int(round((score / max_possible) * 100)))
        if pct >= 25:
            matches.append({
                'prn': c['prn'],
                'score': pct,
                'reason': ' · '.join(reasons) if reasons else f"Matches profile criteria ({cgpa:.2f} CGPA)"
            })

    matches.sort(key=lambda x: x['score'], reverse=True)

    summary_parts = []
    if detected_branches:
        summary_parts.append("Branch: " + "/".join(lbl for lbl, _ in detected_branches))
    if min_cgpa is not None and max_cgpa is not None:
        summary_parts.append(f"CGPA between {min_cgpa} and {max_cgpa}")
    elif min_cgpa is not None:
        summary_parts.append(f"CGPA {'>' if strict_greater else '>='} {min_cgpa}")
    elif max_cgpa is not None:
        summary_parts.append(f"CGPA {'<' if strict_less else '<='} {max_cgpa}")
    if skill_keywords:
        summary_parts.append("Skills: " + ", ".join(skill_keywords))

    summary_text = (
        f"Filtered {len(matches)} candidate(s) matching " + " · ".join(summary_parts)
        if summary_parts else f"Found {len(matches)} candidate(s) matching '{recruiter_query}'."
    )
    return {'ai_summary': summary_text, 'matches': matches}

@csrf_exempt
def ai_candidate_search(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        recruiter_query = (data.get('query') or '').strip()
        if not recruiter_query:
            return JsonResponse({'error': 'Query is required'}, status=400)

        students = StudentProfile.objects.exclude(prn__startswith='PENDING_')
        candidates_list = []
        for s in students:
            candidates_list.append({
                'prn': s.prn,
                'full_name': s.full_name,
                'branch': s.branch,
                'cgpa': float(s.cgpa) if s.cgpa else 0.0,
                'current_year_study': s.current_year_study or '',
                'graduation_year': s.graduation_year or '',
                'skills': s.skills or '',
                'bio': s.bio or '',
                'open_to_internships': bool(s.open_to_internships)
            })
        if GEMINI_API_KEY:
            try:
                system_prompt = f"""You are the AI Recruitment Assistant for MIT-WPU's MITIn platform.
A recruiter searched for: "{recruiter_query}"

Here is the complete JSON list of registered MIT-WPU candidates from the database:
{json.dumps(candidates_list)}

Instructions:
{{
  "ai_summary": "A clear 1-sentence explanation of what you looked for and how you ranked the candidates.",
  "matches": [
    {{
      "prn": "candidate_prn_string",
      "score": 95,
      "reason": "1-sentence specific reason explaining why this candidate fits the prompt."
    }}
  ]
}}
Sort "matches" from highest score to lowest score."""

                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
                payload = {
                    "contents": [{"parts": [{"text": system_prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.2
                    }
                }

                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={
                        'Content-Type': 'application/json',
                        'x-goog-api-key': GEMINI_API_KEY
                    },
                    method='POST'
                )

                with urllib.request.urlopen(req, timeout=15) as response:
                    res_body = json.loads(response.read().decode('utf-8'))
                    raw_text = res_body['candidates'][0]['content']['parts'][0]['text']
                    parsed_ai = json.loads(raw_text)
                    parsed_ai['source'] = 'gemini'
                    return JsonResponse(parsed_ai, status=200)

            except urllib.error.HTTPError as http_err:
                err_detail = http_err.read().decode('utf-8', errors='ignore')
                print(f"[Gemini API HTTP {http_err.code}]: {err_detail}")
            except Exception as api_err:
                print(f"[Gemini API Error]: {api_err}")
        fallback_result = evaluate_candidates_python_ai(recruiter_query, candidates_list)
        fallback_result['source'] = 'local_fallback'
        return JsonResponse(fallback_result, status=200)

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)
