"""
Prompt templates for LLM explanation generation.
These templates are filled with structured offer data to generate explanations.
"""

SYSTEM_PROMPT = """You are an insurance expert assistant for a Tunisian micro-insurance platform.
Your role is to explain insurance offers clearly and accurately.
You must be:
- Precise and factual
- Transparent about risk factors
- Helpful in suggesting improvements
- Culturally appropriate for Tunisia
- Never invent information not provided in the context

You will receive structured offer data and must generate explanations in French (for Tunisia market)."""


CUSTOMER_EXPLANATION_PROMPT = """Génère une explication claire et détaillée pour le client (petit commerçant tunisien).

Contexte client:
- Type d'activité: {activity_type}
- Gouvernorat: {governorate}
- Surface du magasin: {shop_area_m2} m²
- Valeur des actifs: {assets_value_tnd} TND
- Ouvert la nuit: {open_at_night}
- Équipements de sécurité: {security_features}

Offre sélectionnée par notre système:
- Produit: {template_name} ({template_id})
- Garanties incluses: {coverages}
- Plafond de couverture: {plafond_tnd} TND
- Franchise: {franchise_tnd} TND
- Prime annuelle: {prime_annuelle_tnd} TND

Raisons de sélection:
{decision_reasons}

Facteurs de risque identifiés:
{risk_factors}

Composantes du prix:
- Risque de sinistre estimé: {p_claim}
- Coût moyen en cas de sinistre: {expected_cost} TND
- Ajustement sécurité: {feature_adjustment}

Consignes:
1. Explique POURQUOI notre système a sélectionné précisément ce produit pour son profil (3-4 phrases)
2. Détaille comment les caractéristiques de son commerce ont influencé le choix (2-3 phrases)
3. Justifie le prix de manière transparente en expliquant les principaux facteurs (3-4 phrases)
4. Explique comment les garanties correspondent aux risques identifiés (2-3 phrases)
5. Suggère brièvement ce qu'il peut améliorer (1-2 phrases)
6. Ton amical, professionnel et éducatif
7. Maximum 12-15 lignes au total
8. En français tunisien standard

Génère l'explication client:"""


INSURER_EXPLANATION_PROMPT = """Génère une analyse technique détaillée pour le souscripteur / l'assureur.

PROFIL DU CLIENT:
- Type d'activité: {activity_type}
- Gouvernorat: {governorate}
- Surface: {shop_area_m2} m² | Actifs: {assets_value_tnd} TND
- Ouverture nocturne: {open_at_night}
- Sécurité: Alarme={security_alarm}, Caméra={security_camera}, Extincteur={fire_extinguisher}

SEGMENTATION & RISQUE:
- Segment ML identifié: {segment_name}
- Probabilité de sinistre: {p_claim}
- Coût moyen attendu (si sinistre): {expected_cost} TND
- Perte attendue annuelle: {expected_loss} TND
- Score d'incertitude: {uncertainty_score}

LOGIQUE DE SÉLECTION:
- Template sélectionné: {template_id} - {template_name}
- Règles métier déclenchées: {decision_reasons}
- Flags d'attention: {flags}
- Plafond: {plafond_tnd} TND | Franchise: {franchise_tnd} TND

DÉCOMPOSITION DE LA PRIME:
1. Base de risque pur: {expected_loss} TND
2. Multiplicateur appliqué: {multiplier}x
3. Chargement (frais + marge): {expense_margin}
4. Buffer d'incertitude: {uncertainty_buffer}
5. Ajustement sécurité: {feature_adjustment}
→ Prime finale: {prime_annuelle_tnd} TND

FACTEURS AGGRAVANTS:
{aggravating_factors}

FACTEURS ATTÉNUANTS:
{mitigating_factors}

Consignes:
1. Explique POURQUOI le pipeline a sélectionné ce template spécifique (3-4 phrases)
2. Détaille la logique des règles métier déclenchées (2-3 phrases)
3. Analyse les drivers de risque principaux et leur impact quantitatif (4-5 points)
4. Justifie chaque ajustement tarifaire avec son impact (3-4 points)
5. Évalue la cohérence entre le profil et l'offre générée (2-3 phrases)
6. Mentionne tout flag d'attention et recommandations pour la souscription (1-2 phrases)
7. Ton technique, factuel et analytique
8. Maximum 15-18 lignes

Génère l'analyse technique:"""


RECOMMENDATIONS_PROMPT = """Génère 3-5 recommandations concrètes et chiffrées pour optimiser la prime.

PROFIL ACTUEL:
- Type d'activité: {activity_type}
- Ouvert la nuit: {open_at_night}
- Alarme: {security_alarm}
- Caméra: {security_camera}
- Extincteur: {fire_extinguisher}

FACTEURS DE RISQUE ACTUELS:
{risk_factors}

COMPOSANTES TARIFAIRES:
- Prime actuelle: {prime_annuelle_tnd} TND
- Probabilité de sinistre: {p_claim}
- Ajustement sécurité actuel: {feature_adjustment}
- Raisons de sélection: {decision_reasons}

Consignes:
1. Identifie 3-5 actions concrètes et réalistes pour réduire la prime
2. Priorise par impact (commence par le plus impactant)
3. Estime l'impact potentiel (qualitatif + estimation %: "réduction modérée (-10-15%)", "réduction significative (-20-30%)")
4. Explique POURQUOI chaque action réduirait le risque du point de vue du pipeline
5. Sois spécifique (pas de généralités)
6. Maximum 10 lignes
7. En français

Format de sortie:
• Action 1 → Impact attendu + Explication courte
• Action 2 → Impact attendu + Explication courte
• Action 3 → Impact attendu + Explication courte
[...]

Génère les recommandations:"""


DISCLAIMER_TEXT = """⚠️ Estimation basée sur les informations fournies. 
Offre finale sujette à validation après inspection et vérification des documents."""


def format_customer_prompt(client_profile: dict, offer: dict, risk_summary: dict) -> str:
    """Format the customer explanation prompt with actual data."""
    
    # Format security features as readable list
    security_features = []
    if client_profile.get('security_alarm'):
        security_features.append("alarme")
    if client_profile.get('security_camera'):
        security_features.append("caméra")
    if client_profile.get('fire_extinguisher'):
        security_features.append("extincteur")
    
    security_text = ", ".join(security_features) if security_features else "aucun équipement déclaré"
    
    # Format risk factors
    risk_factors_text = "\n".join([f"- {factor}" for factor in risk_summary.get('main_factors', [])])
    
    # Format decision reasons for customer
    decision_reasons = offer.get('decision_reasons', [])
    decision_text = ", ".join(decision_reasons) if decision_reasons else "Profil standard"
    
    # Extract breakdown
    breakdown = offer.get('breakdown', {})
    
    return CUSTOMER_EXPLANATION_PROMPT.format(
        activity_type=client_profile.get('activity_type', 'N/A'),
        governorate=client_profile.get('governorate', 'N/A'),
        shop_area_m2=client_profile.get('shop_area_m2', 'N/A'),
        assets_value_tnd=client_profile.get('assets_value_tnd', 'N/A'),
        open_at_night="Oui" if client_profile.get('open_at_night') else "Non",
        security_features=security_text,
        template_id=offer.get('template_id', 'N/A'),
        template_name=offer.get('template_name', 'N/A'),
        coverages=", ".join(offer.get('coverages', [])),
        plafond_tnd=offer.get('plafond_tnd', 0),
        franchise_tnd=offer.get('franchise_tnd', 0),
        prime_annuelle_tnd=round(offer.get('prime_annuelle_tnd', 0), 2),
        decision_reasons=decision_text,
        risk_factors=risk_factors_text,
        p_claim=f"{breakdown.get('p_claim', 0):.1%}",
        expected_cost=breakdown.get('expected_cost', 0),
        feature_adjustment=breakdown.get('feature_adjustment', 1.0)
    )


def format_insurer_prompt(client_profile: dict, offer: dict, ml_outputs: dict) -> str:
    """Format the insurer explanation prompt with technical details."""
    
    # Format decision reasons
    reasons_text = ", ".join(offer.get('decision_reasons', [])) if offer.get('decision_reasons') else "Standard"
    
    # Format flags
    flags = offer.get('flags', {})
    flags_text = ", ".join([f"{k}={v}" for k, v in flags.items()]) if flags else "Aucun"
    
    # Extract breakdown
    breakdown = offer.get('breakdown', {})
    
    # Format aggravating factors
    aggravating = []
    if client_profile.get('open_at_night'):
        aggravating.append("Ouverture nocturne (+risque vol)")
    if not client_profile.get('security_alarm'):
        aggravating.append("Absence d'alarme (+risque cambriolage)")
    if not client_profile.get('security_camera'):
        aggravating.append("Absence de caméra (+risque non-détection)")
    if breakdown.get('p_claim', 0) > 0.15:
        aggravating.append(f"Fréquence sinistres élevée ({breakdown.get('p_claim', 0):.2%})")
    if client_profile.get('assets_value_tnd', 0) > 50000:
        aggravating.append(f"Actifs élevés ({client_profile.get('assets_value_tnd', 0):,.0f} TND)")
    
    aggravating_text = "\n".join([f"- {factor}" for factor in aggravating]) if aggravating else "- Aucun facteur majeur"
    
    # Format mitigating factors
    mitigating = []
    if client_profile.get('security_alarm'):
        mitigating.append("Présence d'alarme (détection rapide)")
    if client_profile.get('security_camera'):
        mitigating.append("Présence de caméra (dissuasion + preuve)")
    if client_profile.get('fire_extinguisher'):
        mitigating.append("Présence d'extincteur (prévention incendie)")
    if breakdown.get('feature_adjustment', 1.0) < 1.0:
        mitigating.append(f"Ajustement sécurité favorable ({breakdown.get('feature_adjustment', 1.0):.2f})")
    if not client_profile.get('open_at_night'):
        mitigating.append("Fermeture nocturne (-risque vol)")
    
    mitigating_text = "\n".join([f"- {factor}" for factor in mitigating]) if mitigating else "- Aucun facteur notable"
    
    return INSURER_EXPLANATION_PROMPT.format(
        activity_type=client_profile.get('activity_type', 'N/A'),
        governorate=client_profile.get('governorate', 'N/A'),
        shop_area_m2=client_profile.get('shop_area_m2', 'N/A'),
        assets_value_tnd=client_profile.get('assets_value_tnd', 'N/A'),
        open_at_night="Oui" if client_profile.get('open_at_night') else "Non",
        security_alarm="Oui" if client_profile.get('security_alarm') else "Non",
        security_camera="Oui" if client_profile.get('security_camera') else "Non",
        fire_extinguisher="Oui" if client_profile.get('fire_extinguisher') else "Non",
        segment_name=ml_outputs.get('segment_name', 'N/A'),
        p_claim=f"{breakdown.get('p_claim', 0):.2%}",
        expected_cost=breakdown.get('expected_cost', 0),
        expected_loss=breakdown.get('expected_loss', 0),
        uncertainty_score=ml_outputs.get('uncertainty_score', 'N/A'),
        template_id=offer.get('template_id', 'N/A'),
        template_name=offer.get('template_name', 'N/A'),
        decision_reasons=reasons_text,
        flags=flags_text,
        plafond_tnd=offer.get('plafond_tnd', 0),
        franchise_tnd=offer.get('franchise_tnd', 0),
        multiplier=breakdown.get('multiplier', 1.0),
        expense_margin=f"{breakdown.get('expense_margin', 0):.1%}",
        uncertainty_buffer=f"{breakdown.get('uncertainty_buffer', 0):.1%}",
        feature_adjustment=breakdown.get('feature_adjustment', 1.0),
        prime_annuelle_tnd=round(offer.get('prime_annuelle_tnd', 0), 2),
        aggravating_factors=aggravating_text,
        mitigating_factors=mitigating_text
    )


def format_recommendations_prompt(client_profile: dict, offer: dict, risk_summary: dict) -> str:
    """Format the recommendations prompt."""
    
    risk_factors_text = "\n".join([f"- {factor}" for factor in risk_summary.get('main_factors', [])])
    
    # Extract breakdown
    breakdown = offer.get('breakdown', {})
    
    # Format decision reasons
    decision_reasons = ", ".join(offer.get('decision_reasons', [])) if offer.get('decision_reasons') else "Profil standard"
    
    return RECOMMENDATIONS_PROMPT.format(
        activity_type=client_profile.get('activity_type', 'N/A'),
        open_at_night="Oui" if client_profile.get('open_at_night') else "Non",
        security_alarm="Oui" if client_profile.get('security_alarm') else "Non",
        security_camera="Oui" if client_profile.get('security_camera') else "Non",
        fire_extinguisher="Oui" if client_profile.get('fire_extinguisher') else "Non",
        risk_factors=risk_factors_text,
        prime_annuelle_tnd=round(offer.get('prime_annuelle_tnd', 0), 2),
        p_claim=f"{breakdown.get('p_claim', 0):.1%}",
        feature_adjustment=breakdown.get('feature_adjustment', 1.0),
        decision_reasons=decision_reasons
    )