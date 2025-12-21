"""
LLM Explanation Layer - Generates human-readable explanations for insurance offers.
Uses Google Gemini API (free tier).

CRITICAL: LLM is NON-DECISIONAL. It only explains decisions made by rules + pricing engine.
"""

from typing import Dict, Any, Optional
from google import genai
from dataclasses import dataclass
import os

from .prompts import (
    SYSTEM_PROMPT,
    DISCLAIMER_TEXT,
    format_customer_prompt,
    format_insurer_prompt,
    format_recommendations_prompt
)


@dataclass
class ExplanationOutput:
    """Structured output from LLM explanation layer."""
    customer_explanation: str
    insurer_explanation: str
    recommendations: str
    disclaimer: str
    
    def to_dict(self) -> dict:
        return {
            'customer_explanation': self.customer_explanation,
            'insurer_explanation': self.insurer_explanation,
            'recommendations': self.recommendations,
            'disclaimer': self.disclaimer
        }


class OfferExplainer:
    """
    LLM-powered explanation generator for insurance offers.
    
    Architecture position: Layer 5 (Explanation Layer)
    - Receives: Offer (from pricing engine) + ML outputs + client profile
    - Produces: 3 explanations (customer, insurer, recommendations)
    - DOES NOT: Make decisions, change prices, select templates
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash-lite"):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google API key (if None, uses fallback mode without LLM)
            model: Gemini model to use (default: gemini-2.0-flash-exp for free tier)
        """
        self.api_key = api_key
        self.model = model
        
        # Only initialize client if API key is provided
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.client = None
    
    def generate_explanations(
        self,
        offer: Dict[str, Any],
        client_profile: Dict[str, Any],
        ml_outputs: Optional[Dict[str, Any]] = None
    ) -> ExplanationOutput:
        """
        Generate all explanations for a given offer.
        
        Args:
            offer: Output from pricing engine (dict or Offer dataclass)
            client_profile: Input features from client form
            ml_outputs: Optional ML model outputs (segment, uncertainty, etc.)
        
        Returns:
            ExplanationOutput with 3 explanations + disclaimer
        """
        
        # Convert offer to dict if needed
        if hasattr(offer, '__dict__'):
            offer_dict = offer.__dict__
        else:
            offer_dict = offer
        
        # Prepare ML outputs (defaults if not provided)
        if ml_outputs is None:
            ml_outputs = {
                'segment_name': 'Standard',
                'uncertainty_score': 'Modéré'
            }
        
        # Prepare risk summary
        risk_summary = self._extract_risk_summary(offer_dict, client_profile)
        
        # Generate each explanation
        customer_exp = self._generate_customer_explanation(client_profile, offer_dict, risk_summary)
        insurer_exp = self._generate_insurer_explanation(client_profile, offer_dict, ml_outputs)
        recommendations = self._generate_recommendations(client_profile, offer_dict, risk_summary)
        
        return ExplanationOutput(
            customer_explanation=customer_exp,
            insurer_explanation=insurer_exp,
            recommendations=recommendations,
            disclaimer=DISCLAIMER_TEXT
        )
    
    def _extract_risk_summary(self, offer: dict, client_profile: dict) -> dict:
        """Extract main risk factors from offer and profile."""
        
        main_factors = []
        
        # Extract from decision reasons
        reasons = offer.get('decision_reasons', [])
        if 'rule_open_at_night' in reasons:
            main_factors.append("Commerce ouvert la nuit (risque vol majoré)")
        if 'rule_high_frequency' in reasons:
            main_factors.append("Historique de sinistralité dans le secteur")
        if 'rule_high_assets' in reasons:
            main_factors.append("Valeur élevée des actifs à protéger")
        
        # Extract from profile
        if not client_profile.get('security_alarm'):
            main_factors.append("Absence de système d'alarme")
        if not client_profile.get('security_camera'):
            main_factors.append("Absence de caméra de surveillance")
        
        # Extract from breakdown
        breakdown = offer.get('breakdown', {})
        if breakdown.get('p_claim', 0) > 0.15:
            main_factors.append(f"Probabilité de sinistre élevée ({breakdown.get('p_claim', 0):.1%})")
        
        return {
            'main_factors': main_factors if main_factors else ["Profil de risque standard"]
        }
    
    def _generate_customer_explanation(
        self, 
        client_profile: dict, 
        offer: dict, 
        risk_summary: dict
    ) -> str:
        """Generate customer-facing explanation (simple language)."""
        
        # Use fallback if no client available
        if self.client is None:
            return self._fallback_customer_explanation(offer)
        
        prompt = format_customer_prompt(client_profile, offer, risk_summary)
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
                    {"role": "model", "parts": [{"text": "Compris. Je génère des explications claires en français pour le marché tunisien."}]},
                    {"role": "user", "parts": [{"text": prompt}]}
                ]
            )
            return response.text.strip()
        except Exception as e:
            # Fallback if LLM fails
            return self._fallback_customer_explanation(offer)
    
    def _generate_insurer_explanation(
        self, 
        client_profile: dict, 
        offer: dict, 
        ml_outputs: dict
    ) -> str:
        """Generate insurer-facing technical analysis."""
        
        # Use fallback if no client available
        if self.client is None:
            return self._fallback_insurer_explanation(offer)
        
        prompt = format_insurer_prompt(client_profile, offer, ml_outputs)
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
                    {"role": "model", "parts": [{"text": "Compris. Je génère une analyse technique pour souscripteur."}]},
                    {"role": "user", "parts": [{"text": prompt}]}
                ]
            )
            return response.text.strip()
        except Exception as e:
            return self._fallback_insurer_explanation(offer)
    
    def _generate_recommendations(
        self, 
        client_profile: dict, 
        offer: dict, 
        risk_summary: dict
    ) -> str:
        """Generate actionable recommendations to reduce premium."""
        
        # Use fallback if no client available
        if self.client is None:
            return self._fallback_recommendations(client_profile)
        
        prompt = format_recommendations_prompt(client_profile, offer, risk_summary)
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
                    {"role": "model", "parts": [{"text": "Compris. Je génère des recommandations concrètes."}]},
                    {"role": "user", "parts": [{"text": prompt}]}
                ]
            )
            return response.text.strip()
        except Exception as e:
            return self._fallback_recommendations(client_profile)
    
    # ============== FALLBACK METHODS (if LLM fails) ==============
    
    def _fallback_customer_explanation(self, offer: dict) -> str:
        """Simple fallback if LLM is unavailable."""
        return f"""Nous avons sélectionné l'offre "{offer.get('template_name')}" adaptée à votre activité.
Cette couverture protège vos actifs jusqu'à {offer.get('plafond_tnd', 0):,.0f} TND avec une prime annuelle de {offer.get('prime_annuelle_tnd', 0):.2f} TND.
Votre franchise (montant à votre charge) est de {offer.get('franchise_tnd', 0):,.0f} TND par sinistre."""
    
    def _fallback_insurer_explanation(self, offer: dict) -> str:
        """Technical fallback if LLM is unavailable."""
        breakdown = offer.get('breakdown', {})
        return f"""Template: {offer.get('template_id')} sélectionné selon règles métier.
Fréquence attendue: {breakdown.get('p_claim', 0):.2%} | Coût moyen: {breakdown.get('expected_cost', 0):,.0f} TND
Perte attendue: {breakdown.get('expected_loss', 0):,.0f} TND | Chargement: {breakdown.get('expense_margin', 0):.1%}
Flags: {', '.join([f"{k}={v}" for k, v in offer.get('flags', {}).items()])}"""
    
    def _fallback_recommendations(self, client_profile: dict) -> str:
        """Simple fallback recommendations."""
        reco = []
        if not client_profile.get('security_alarm'):
            reco.append("• Installer un système d'alarme → Réduction modérée")
        if not client_profile.get('security_camera'):
            reco.append("• Installer une caméra de surveillance → Réduction modérée")
        if client_profile.get('open_at_night'):
            reco.append("• Limiter les heures d'ouverture nocturne → Réduction significative")
        
        return "\n".join(reco) if reco else "• Profil déjà optimisé"


# ============== STANDALONE TEST FUNCTION ==============

def test_explainer_local():
    """Test the explainer with sample data (offline mode)."""
    
    # Sample offer (from your example)
    sample_offer = {
        'template_id': 'T3_NIGHT',
        'template_name': 'Night & Cash Risk',
        'coverages': ['theft_extended', 'cash_on_premises', 'vandalism'],
        'plafond_tnd': 36000.0,
        'franchise_tnd': 2400,
        'prime_annuelle_tnd': 638.93,
        'breakdown': {
            'expected_cost': 2500.0,
            'expected_loss': 450.0,
            'expense_margin': 0.45,
            'feature_adjustment': 0.986,
            'multiplier': 1.6,
            'p_claim': 0.18,
            'uncertainty_buffer': 0.15
        },
        'decision_reasons': ['rule_open_at_night', 'rule_high_frequency'],
        'flags': {'high_risk': False, 'underwriting_review': False}
    }
    
    # Sample client profile
    sample_profile = {
        'activity_type': 'Café',
        'governorate': 'Tunis',
        'shop_area_m2': 45,
        'assets_value_tnd': 40000,
        'open_at_night': True,
        'security_alarm': False,
        'security_camera': True,
        'fire_extinguisher': True
    }
    
    # Sample ML outputs
    sample_ml = {
        'segment_name': 'Cluster 2 - Risque Élevé',
        'uncertainty_score': 'Élevé'
    }
    
    print("=" * 60)
    print("Testing LLM Explainer (Fallback Mode - No API Key)")
    print("=" * 60)
    print("ENV GOOGLE_API_KEY exists?", bool(os.getenv("GOOGLE_API_KEY")))
    print("ENV GOOGLE_API_KEY prefix:", (os.getenv("GOOGLE_API_KEY") or "")[:6])

    # Test without API key (uses fallback)
    explainer = OfferExplainer(api_key=os.getenv("GOOGLE_API_KEY"))
    
    explanations = explainer.generate_explanations(
        offer=sample_offer,
        client_profile=sample_profile,
        ml_outputs=sample_ml
    )
    
    print("\n📋 CUSTOMER EXPLANATION:")
    print(explanations.customer_explanation)
    
    print("\n🔍 INSURER EXPLANATION:")
    print(explanations.insurer_explanation)
    
    print("\n💡 RECOMMENDATIONS:")
    print(explanations.recommendations)
    
    print("\n⚠️ DISCLAIMER:")
    print(explanations.disclaimer)
    
    print("\n" + "=" * 60)
    print("✅ Test completed successfully")
    print("=" * 60)


if __name__ == "__main__":
    test_explainer_local()