"""
ベンダー推薦Lambda関数
- S3からvendors.csvを読み込み
- Bedrock (Claude 3.5 Sonnet)でベンダー推薦
- PJ要件適合度と戦略スコアを計算
"""
import json
import os
import csv
import io
import boto3
from typing import Dict, List, Any

# 環境変数
S3_BUCKET = os.getenv("S3_BUCKET")
CSV_KEY = os.getenv("CSV_KEY", "vendors.csv")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-1")

# Bedrock クライアント
BEDROCK = boto3.client("bedrock-runtime", region_name=AWS_REGION)
S3_CLIENT = boto3.client("s3", region_name=AWS_REGION)
LLM_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"


def _response(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """HTTPレスポンスを生成（CORSヘッダー付き）"""
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST,OPTIONS"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }


def load_vendors_from_s3() -> List[Dict[str, Any]]:
    """S3からvendors.csvを読み込む"""
    try:
        response = S3_CLIENT.get_object(Bucket=S3_BUCKET, Key=CSV_KEY)
        csv_content = response["Body"].read().decode("utf-8-sig")
        
        # CSVをパース
        reader = csv.DictReader(io.StringIO(csv_content))
        vendors = []
        for row in reader:
            # 数値フィールドを変換
            try:
                row["employee_count"] = int(row.get("employee_count", 0) or 0)
            except (ValueError, TypeError):
                row["employee_count"] = 0
            
            try:
                row["aws_capability"] = int(row.get("aws_capability", 0) or 0)
            except (ValueError, TypeError):
                row["aws_capability"] = 0
            
            try:
                row["internal_dev_support"] = int(row.get("internal_dev_support", 0) or 0)
            except (ValueError, TypeError):
                row["internal_dev_support"] = 0
            
            try:
                row["ip_flexibility"] = int(row.get("ip_flexibility", 0) or 0)
            except (ValueError, TypeError):
                row["ip_flexibility"] = 0
            
            vendors.append(row)
        
        return vendors
    except Exception as e:
        print(f"Error loading CSV from S3: {str(e)}")
        raise


def calculate_strategic_score(vendor: Dict[str, Any]) -> int:
    """
    戦略スコア（0-100点）を計算
    A領域（M&A候補）条件該当数で計算
    """
    score = 0
    max_score = 100
    
    # 条件1: employee_count: 5-15人 (30点)
    employee_count = vendor.get("employee_count", 0)
    if 5 <= employee_count <= 15:
        score += 30
    
    # 条件2: internal_dev_support >= 4 (25点)
    if vendor.get("internal_dev_support", 0) >= 4:
        score += 25
    
    # 条件3: aws_capability >= 3 (25点)
    if vendor.get("aws_capability", 0) >= 3:
        score += 25
    
    # 条件4: ip_flexibility >= 3 (20点)
    if vendor.get("ip_flexibility", 0) >= 3:
        score += 20
    
    return min(score, max_score)


def evaluate_vendor_with_bedrock(
    vendor: Dict[str, Any],
    user_requirements: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Bedrock (Claude 3.5 Sonnet)でベンダーを評価
    PJ要件適合度（0-100点）と推薦理由を生成
    """
    # ベンダー情報を整形
    vendor_info = f"""
会社名: {vendor.get('company_name', '')}
従業員数: {vendor.get('employee_count', 0)}人
設立年: {vendor.get('foundation_year', '')}
本社: {vendor.get('headquarters', '')}
事業モデル: {vendor.get('business_model', '')}
技術スタック: {vendor.get('tech_stack', '')}
ドメイン専門性: {vendor.get('domain_expertise', '')}
専門性タイプ: {vendor.get('specialization_type', '')}
AWS能力: {vendor.get('aws_capability', 0)}/5
内製化支援: {vendor.get('internal_dev_support', 0)}/5
IP柔軟性: {vendor.get('ip_flexibility', 0)}/5
技術深度: {vendor.get('technical_depth', 0)}/5
コンサル能力: {vendor.get('consulting_capability', 0)}/5
サポートモデル: {vendor.get('support_model', '')}
備考: {vendor.get('notes', '')}
"""
    
    # ユーザー要件を整形
    requirements = f"""
重視項目: {', '.join(user_requirements.get('priorities', []))}
開発体制: {user_requirements.get('developmentStyle', '')}
企業規模: {user_requirements.get('companySize', '')}
技術要件: {', '.join(user_requirements.get('techStack', []))}
対象業界: {user_requirements.get('industry', '')}
所有権希望: {user_requirements.get('ipOwnership', '')}
パートナーシップ: {user_requirements.get('partnership', '')}
"""
    
    # プロンプト作成
    prompt = f"""あなたはAIベンダー選定の専門家です。以下のベンダー情報とユーザー要件を比較して、プロジェクト要件適合度を0-100点で評価してください。

【ベンダー情報】
{vendor_info}

【ユーザー要件】
{requirements}

【評価基準】
1. 技術要件の適合度（AWS、AI/ML、モダンWeb技術など）
2. 開発体制の希望との一致度（完全受託、協働開発、内製支援など）
3. 企業規模の希望との一致度
4. 業界・ドメインの専門性
5. 所有権・IP柔軟性の希望との一致度
6. パートナーシップ志向との一致度

【出力形式】
以下のJSON形式で出力してください：
{{
  "pj_match_score": 85,
  "reasoning": "推薦理由を200-300文字の自然な日本語で記述してください。このベンダーがなぜユーザーの要件に適合するのか、具体的な強みや特徴を説明してください。"
}}

重要: JSONのみを出力し、それ以外のテキストは含めないでください。"""
    
    try:
        # Bedrock呼び出し
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]
        }
        
        response = BEDROCK.invoke_model(
            modelId=LLM_MODEL,
            body=json.dumps(body)
        )
        
        result = json.loads(response["body"].read())
        answer_text = result["content"][0]["text"].strip()
        
        # JSONを抽出（```json で囲まれている場合がある）
        if "```json" in answer_text:
            answer_text = answer_text.split("```json")[1].split("```")[0].strip()
        elif "```" in answer_text:
            answer_text = answer_text.split("```")[1].split("```")[0].strip()
        
        evaluation = json.loads(answer_text)
        
        return {
            "pj_match_score": int(evaluation.get("pj_match_score", 0)),
            "reasoning": evaluation.get("reasoning", "")
        }
    except Exception as e:
        print(f"Error evaluating vendor with Bedrock: {str(e)}")
        # フォールバック: 簡易スコアリング
        return {
            "pj_match_score": 50,
            "reasoning": "評価処理中にエラーが発生しました。"
        }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda ハンドラー
    入力JSONを受け取り、ベンダー推薦結果を返す
    """
    try:
        # OPTIONSリクエスト（CORS preflight）の処理
        if event.get("httpMethod") == "OPTIONS":
            return _response(200, {})
        
        # リクエストボディの取得
        if event.get("body"):
            if isinstance(event["body"], str):
                body = json.loads(event["body"])
            else:
                body = event["body"]
        else:
            return _response(400, {"error": "Missing request body"})
        
        # ユーザー要件の取得
        user_requirements = {
            "priorities": body.get("priorities", []),
            "developmentStyle": body.get("developmentStyle", ""),
            "companySize": body.get("companySize", ""),
            "techStack": body.get("techStack", []),
            "industry": body.get("industry", ""),
            "ipOwnership": body.get("ipOwnership", ""),
            "partnership": body.get("partnership", ""),
        }
        
        # S3からベンダーリストを読み込み
        vendors = load_vendors_from_s3()
        
        # 各ベンダーを評価
        evaluations = []
        for vendor in vendors:
            # PJ要件適合度をBedrockで評価
            bedrock_result = evaluate_vendor_with_bedrock(vendor, user_requirements)
            pj_score = bedrock_result["pj_match_score"]
            reasoning = bedrock_result["reasoning"]
            
            # 戦略スコアを計算
            strategic_score = calculate_strategic_score(vendor)
            
            # 総合スコア = 0.6 × PJ適合度 + 0.4 × 戦略スコア
            total_score = int(0.6 * pj_score + 0.4 * strategic_score)
            
            evaluations.append({
                "company_name": vendor.get("company_name", ""),
                "match_score": total_score,
                "pj_match_score": pj_score,
                "strategic_score": strategic_score,
                "reasoning": reasoning,
                "vendor_data": vendor  # デバッグ用（本番では削除可）
            })
        
        # スコアでソート（降順）
        evaluations.sort(key=lambda x: x["match_score"], reverse=True)
        
        # 上位3社を取得
        top3 = evaluations[:3]
        
        # レスポンス形式に整形
        recommendations = [
            {
                "company_name": item["company_name"],
                "match_score": item["match_score"],
                "reasoning": item["reasoning"]
            }
            for item in top3
        ]
        
        return _response(200, {
            "recommendations": recommendations
        })
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return _response(500, {"error": str(e)})
