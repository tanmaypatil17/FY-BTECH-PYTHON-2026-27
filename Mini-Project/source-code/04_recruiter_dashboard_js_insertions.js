const searchForm = document.getElementById('ai-search-form');
      const searchInput = document.getElementById('ai-search-input');
      const clearBtn = document.getElementById('clear-search-btn');
      const insightsBanner = document.getElementById('ai-insights-banner');
      const analysisSummary = document.getElementById('ai-analysis-summary');
      const candidatesGrid = document.getElementById('candidates-grid');
      const noMatchesBox = document.getElementById('no-ai-matches');
      const countPill = document.getElementById('candidate-count-pill');

      async function runAICandidateSearch(queryText) {
        const query = queryText.trim();
        if (!query) {
          resetAISearch();
          return;
        }

        clearBtn.classList.remove('hidden');
        const submitBtn = searchForm.querySelector('button[type="submit"]');
        const originalBtnText = submitBtn.innerHTML;
        submitBtn.innerHTML = '✨ Gemini Analyzing...';
        submitBtn.disabled = true;

        try {
          const res = await fetch('/api/ai-search/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
          });

          if (res.ok) {
            const aiData = await res.json();
            const matches = aiData.matches || [];
            const engineLabel = aiData.source === 'gemini'
              ? '✨ Google Gemini 2.5'
              : '✨ MITIn AI Engine';
            analysisSummary.textContent = `${engineLabel}: ${aiData.ai_summary || 'Evaluated all candidate profiles.'}`;
            insightsBanner.classList.remove('hidden');
            allCards.forEach(card => {
              card.classList.add('hidden');
              const reasonBox = card.querySelector('.ai-reason-box');
              if (reasonBox) reasonBox.classList.add('hidden');
            });

            const matchedCards = [];
            matches.forEach(matchItem => {
              const card = allCards.find(c => c.getAttribute('data-prn') === String(matchItem.prn));
              if (card) {
                card.classList.remove('hidden');
                const badge = card.querySelector('.ai-match-badge');
                const scoreText = card.querySelector('.ai-score-text');
                if (badge && scoreText) {
                  scoreText.textContent = `${matchItem.score || 95}% Match`;
                  badge.classList.remove('hidden');
                }
                const reasonBox = card.querySelector('.ai-reason-box');
                if (reasonBox && matchItem.reason) {
                  reasonBox.textContent = `💡 ${matchItem.reason}`;
                  reasonBox.classList.remove('hidden');
                }
                candidatesGrid.appendChild(card);
                matchedCards.push(card);
              }
            });

            countPill.textContent = `${matchedCards.length} AI Matches Found`;
            noMatchesBox.classList.toggle('hidden', matchedCards.length > 0);
          } else {
            const errData = await res.json();
            alert(errData.error || 'AI Search failed.');
          }
        } catch (err) {
          console.error('AI Search fetch error:', err);
          alert('Could not reach Django AI Search endpoint. Make sure python manage.py runserver is running.');
        } finally {
          submitBtn.innerHTML = originalBtnText;
          submitBtn.disabled = false;
        }
      }

      function resetAISearch() {
        searchInput.value = '';
        clearBtn.classList.add('hidden');
        insightsBanner.classList.add('hidden');
        noMatchesBox.classList.add('hidden');

        allCards.forEach(card => {
          card.classList.remove('hidden');
          const badge = card.querySelector('.ai-match-badge');
          if (badge) badge.classList.add('hidden');
          const reasonBox = card.querySelector('.ai-reason-box');
          if (reasonBox) reasonBox.classList.add('hidden');
          card.querySelectorAll('.skill-tag').forEach(tag => {
            tag.classList.remove('bg-blue-100', 'border-blue-300', 'text-blue-900');
            tag.classList.add('bg-gray-50', 'text-gray-700');
          });
          candidatesGrid.appendChild(card);
        });

        countPill.textContent = `${allCards.length} Candidates Found`;
      }

      searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        runAICandidateSearch(searchInput.value);
      });

      searchInput.addEventListener('input', () => {
        if (searchInput.value.trim() === '') resetAISearch();
      });

      clearBtn.addEventListener('click', resetAISearch);
      document.getElementById('reset-ai-filter').addEventListener('click', resetAISearch);
      document.getElementById('empty-reset-btn').addEventListener('click', resetAISearch);

      document.querySelectorAll('.ai-chip').forEach(chip => {
        chip.addEventListener('click', () => {
          const promptText = chip.getAttribute('data-prompt');
          searchInput.value = promptText;
          runAICandidateSearch(promptText);
        });
      });
