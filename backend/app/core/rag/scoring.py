class EvidenceScorer:
    @staticmethod
    def calculate_confidence(matches: list) -> dict:
        """
        Calculates a transparent evidence score based on retrieval signals.
        Returns:
            confidence score (0-100)
            confidence level (LOW, MEDIUM, HIGH)
            evidence count
            supporting document count
            retrieval quality (average relevance)
        """
        if not matches:
            return {
                "confidence": 0,
                "level": "NONE",
                "evidence_count": 0,
                "supporting_documents": 0,
                "retrieval_quality": 0.0,
                "citation_coverage": "0%"
            }

        evidence_count = len(matches)
        
        # Calculate retrieval quality (average score of retrieved chunks)
        scores = [m.get("score", 0.0) for m in matches]
        retrieval_quality = sum(scores) / evidence_count
        
        # Count distinct documents
        doc_ids = set()
        for m in matches:
            doc_id = m.get("metadata", {}).get("document_id")
            if doc_id:
                doc_ids.add(doc_id)
        supporting_docs = len(doc_ids)
        
        # Heuristic scoring logic
        # 1. Base score derived from average retrieval quality (max 60 points)
        base_score = min(retrieval_quality * 60, 60)
        
        # 2. Multi-evidence bonus (up to 20 points)
        evidence_bonus = min(evidence_count * 5, 20)
        
        # 3. Multi-document corroboration bonus (up to 20 points)
        doc_bonus = min(supporting_docs * 10, 20)
        
        confidence = int(base_score + evidence_bonus + doc_bonus)
        
        # Cap at 100
        confidence = min(confidence, 100)
        
        # Determine Level
        if confidence >= 80:
            level = "HIGH"
        elif confidence >= 50:
            level = "MEDIUM"
        else:
            level = "LOW"
            
        return {
            "confidence": confidence,
            "level": level,
            "evidence_count": evidence_count,
            "supporting_documents": supporting_docs,
            "retrieval_quality": round(retrieval_quality, 4),
            "citation_coverage": f"{min(evidence_count * 10, 100)}%" # rough proxy
        }

    @staticmethod
    def rank_matches(matches: list, threshold: float = 0.15) -> list:
        """Ranks evidence matches by score in descending order and filters out irrelevant ones."""
        filtered = [m for m in matches if m.get("score", 0.0) >= threshold]
        return sorted(filtered, key=lambda x: x.get("score", 0.0), reverse=True)

