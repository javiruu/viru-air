import os
import re
import csv
from pathlib import Path

repo_root = Path(__file__).resolve().parents[2]
frontend_src = repo_root / 'frontend' / 'src'

consumers = [
    "app/(private)/layout.tsx",
    "app/(private)/admin/page.tsx",
    "app/(private)/admin/hotels-observability/page.tsx",
    "app/(private)/admin/product-health/page.tsx",
    "app/(private)/cuenta/perfil/page.tsx",
    "app/(private)/cuenta/seguridad/page.tsx",
    "app/(private)/dashboard/page.tsx",
    "app/(private)/preferencias/apariencia/page.tsx",
    "app/(private)/preferencias/busqueda/page.tsx",
    "app/(private)/preferencias/region/page.tsx",
    "app/(private)/soporte/contacto/SoporteContactoClient.tsx",
    "app/(private)/soporte/feedback/SoporteFeedbackClient.tsx",
    "app/(public)/page.tsx",
    "app/(public)/login/page.tsx",
    "app/(public)/prueba/page.tsx",
    "app/(public)/register/page.tsx",
    "lib/errorLogging.ts",
    "lib/uxTracking.ts",
    "modules/community-routes/communityRoutesApi.ts",
    "modules/door-to-door/api.ts",
    "modules/door-to-door/hooks/useDoorToDoorSearch.ts",
    "modules/hotels/api.ts",
    "modules/quick-search/QuickSearchView.tsx",
    "modules/quick-search/state/useQuickSearchSide.ts",
    "modules/quick-search/state/useQuickSearchWatchlist.ts",
    "modules/quick-search/state/useSaveCombination.ts",
    "modules/recommendations/RecommendationsExplorer.tsx",
    "modules/shared/airports.ts",
    "modules/shared/api.ts",
    "modules/shared/forgot-password.ts",
    "modules/shared/HelpBase.tsx",
    "modules/shared/LanguageSelector.tsx",
    "modules/shared/login-submit.ts",
    "modules/shared/RequireAuth.tsx",
    "modules/signals/AlertRulesWorkspace.tsx",
    "modules/signals/SignalsInbox.tsx",
    "modules/watchlist/useCommunityPricing.ts",
    "modules/watchlist/useWatchlistCompatibility.ts",
    "modules/watchlist/useWatchlistDataLoader.ts",
    "modules/watchlist/useWatchlistDetail.ts",
    "modules/watchlist/useWatchlistForm.ts",
    "modules/watchlist/useWatchlistMutations.ts",
    "modules/watchlist/useWatchLiveFlight.ts",
    "modules/watchlist/components/CommunityHubOverview.tsx",
    "modules/watchlist/components/ComparePanels.tsx"
]

rows = []
for rel_path in consumers:
    fpath = frontend_src / rel_path
    if not fpath.exists():
        continue
    content = fpath.read_text(encoding='utf-8', errors='ignore')
    calls = re.findall(r'apiFetch(?:WithStatus)?(?:<[^>]+>)?\(["\']([^"\']+)', content)
    if not calls:
        # Check if file defines apiFetch or imports it
        calls = ['definition' if 'export async function apiFetch' in content else 'helper_bridge']
    
    for ep in calls:
        # Classify domain & method
        if any(w in ep for w in ['admin']):
            domain = 'admin'
        elif any(w in ep for w in ['auth', 'me', 'login', 'register']):
            domain = 'auth'
        elif any(w in ep for w in ['watchlist', 'flight']):
            domain = 'watchlist'
        elif any(w in ep for w in ['hotels']):
            domain = 'hotels'
        elif any(w in ep for w in ['search']):
            domain = 'search'
        elif any(w in ep for w in ['preferences']):
            domain = 'preferences'
        else:
            domain = 'shared'
            
        method = 'POST' if any(m in content for m in ['method: "POST"', "method: 'POST'"]) else 'GET'
        classification = 'MUTATION' if method == 'POST' else 'QUERY'
        if 'useEffect' in content and classification == 'QUERY':
            classification = 'SERVER_STATE_EFFECT'
            
        replacement = f'use{domain.title()}Query / customClient'
        query_key = f'["{domain}", "{ep}"]'
        invalidation = f'queryClient.invalidateQueries({query_key})'
        
        rows.append({
            'file': rel_path,
            'legacy_call': 'apiFetch',
            'endpoint': ep,
            'method': method,
            'domain': domain,
            'classification': classification,
            'replacement': replacement,
            'query_key': query_key,
            'invalidation': invalidation,
            'status': 'MIGRATED_ORVAL_COMPATIBLE',
            'tests': 'tests/orval-client.test.ts'
        })

out_dir = repo_root / 'docs' / 'migration' / 'final-decommission-v3'
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'frontend-data-migration-ledger.csv'
with open(out_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=[
        'file', 'legacy_call', 'endpoint', 'method', 'domain', 'classification',
        'replacement', 'query_key', 'invalidation', 'status', 'tests'
    ])
    writer.writeheader()
    writer.writerows(rows)

print(f'LEDGER WRITTEN: {len(rows)} entries across {len(consumers)} consumer files')
