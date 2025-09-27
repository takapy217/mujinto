import streamlit as st
import streamlit.components.v1 as components
import json, re, base64, time
from pathlib import Path
from typing import Union, Dict, Any

# =============================
# ページ設定
# =============================
st.set_page_config(page_title="無人島からの脱出　vol.1", layout="centered")

# =============================
# 設定（JP固定運用）
# =============================
STORY_FILE = "story_mujinto_1_jp.json"  # ← 日本語JSONに固定
GAME_CLEAR_CHAPTER_DEFAULT = "100"      # ← JSONの clear_chapter が無い場合の既定
CLEAR_IMAGE = "assets/img_gameclear.png"
GAMEOVER_IMAGE = "assets/img_gameover.png"

# =============================
# 端末プロファイル（動画枠の高さ制御）
# =============================
DEVICE_PROFILES: Dict[str, Dict[str, Any]] = {
    "iPhone SE": {"mode": "fixed", "height": 200},
    "Standard Phone":      {"mode": "fixed", "height": 240},
    "Small Phone":         {"mode": "fixed", "height": 216},
    "Tablet":              {"mode": "fixed", "height": 400},
    "Desktop":             {"mode": "fixed", "height": 400},
}

# =============================
# グローバルCSS（余白/画像/動画/ボタン）
# =============================
st.markdown(
    """
<style>
/* コンテナ余白 */
.block-container{padding-top:2rem !important; padding-bottom:0.8rem !important;}

/* 本文 */
.scene-text{
  font-size: 0.95rem;
  line-height: 1.55;
  margin: 6px 0 14px 0;
}
.stMarkdown p{ margin:.35rem 0 !important; }
@media (max-width:480px){ .stMarkdown p{ margin:.28rem 0 !important; } }

/* 画像は角丸OFF＋統一余白 */
.stImage img{
  display:block !important; width:100% !important; height:auto !important;
  margin:0 0 8px 0 !important; border-radius:0 !important; background:#000;
}

/* ボタン（縦並び・左寄せ・余白詰め） */
div.stButton{ margin: 0 0 .30rem 0 !important; }
.stButton > button{
  width:100% !important;
  min-height:44px !important;
  padding:.50rem .70rem !important;
  line-height:1.1 !important;
  justify-content:flex-start !important; /* 中央→左寄せ */
  text-align:left !important;
}
@media (max-width:480px){
  div.stButton{ margin: 0 0 .18rem 0 !important; }
  .stButton > button{ padding:.46rem .60rem !important; font-size:1.02rem !important; }
}

/* 動画フェードイン */
.lowflicker-video{
  opacity:0; transition:opacity .18s ease;
  display:block; width:100%; height:100%;
  object-fit:cover; background:#000;
}
.lowflicker-wrap{ width:100%; height:100%; background:#000; }
</style>
""",
    unsafe_allow_html=True,
)

# =============================
# ヘルパー
# =============================
import requests

WEBAPP_URL = "https://script.google.com/macros/s/AKfycbyBqnMuLsfpeRBDdN9gDOMXIUTSSOHcpEQU1P6kj6DqWXH7FPuNbmwpMIZp_-ua0WJ3pw/exec"  # あなたの/exec URL

def log_clear_to_sheets(score: int, rank: str, msg: str):
    data = {"score": score, "rank": rank, "msg": msg}
    try:
        requests.post(WEBAPP_URL, json=data, timeout=5)
    except Exception as e:
        st.warning(f"ログ送信エラー: {e}")

def get_max_score(story: dict) -> int:
    return int(story.get("max_score", 100))

def calc_rank(score: int, max_score: int = 100):
    if max_score <= 0: max_score = 100
    ratio = (score / max_score) * 100.0
    if ratio >= 95:  return "伝説のサバイバー", "完璧な判断の連続。無人島の方から『もう来るな』と言われている。"
    if ratio >= 90:  return "達人サバイバー", "危機管理は洗練されている。残る課題は…運。"
    if ratio >= 80:  return "上級サバイバー", "安定して高水準。でも慢心は禁物。"
    if ratio >= 70:  return "中級サバイバー", "まあ…死なない程度にはマシ。"
    if ratio >= 60:  return "初級サバイバー", "学びは十分。ただし、無人島生活は非推奨。"
    if ratio >= 40:  return "見習いサバイバー", "救助がなければ、ここでゲームオーバーだった。"
    if ratio >= 20:  return "かろうじて生還", "サバイバルより先に、日常生活から鍛え直そう。"
    if ratio >= 0:   return "瀕死の生還者", "無人島より遊園地の方があなた向き。"

def inject_device_css():
    st.markdown(
        """
<style>
.lowflicker-video{ object-fit:cover !important; }
</style>
""",
        unsafe_allow_html=True,
    )

def load_story() -> Dict[str, Any]:
    p = Path(STORY_FILE)
    if not p.exists():
        return {
            "intro_text": "JSON not found. Please prepare story file.",
            "chapters": {
                "1": {
                    "text": "ダミー章です。JSONを用意してください。",
                    "choices": []
                }
            },
        }
    return json.loads(p.read_text(encoding="utf-8"))

def init_session():
    defaults = {
        "chapter": "start",
        "lp": 0,
        "selected": None,
        "show_result": False,
        "player_name": "",
        "lp_updated": False,
        "vid_seq": 0,
        "device_profile": "Standard Phone",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def personalize(text: str) -> str:
    return re.sub(r"{player_name}", st.session_state.get("player_name", "あなた"), text or "")

def ensure_asset(path: str) -> Path:
    p = Path(path)
    if not (str(p).startswith("assets/") or str(p).startswith("./assets/")):
        p = Path("assets") / p
    return p

def render_text(text: str):
    if not text: return
    st.markdown(f'<div class="scene-text">{personalize(text)}</div>', unsafe_allow_html=True)

# =============================
# 動画描画（AutoPlay安定・フェードイン）
# =============================
def render_video(path: str, *, autoplay=True, muted=True, loop=False, controls=False, height_pc: int = 360):
    st.session_state.vid_seq += 1
    vid_id = f"v{st.session_state.vid_seq}"

    p = ensure_asset(path)
    if not p.exists():
        st.warning(f"Video not found: {p}")
        return

    b64 = base64.b64encode(p.read_bytes()).decode("utf-8")
    prof = DEVICE_PROFILES.get(st.session_state.get("device_profile", "Standard Phone")) or {}
    iframe_h = int(prof.get("height") or height_pc)

    attrs = []
    if autoplay: attrs.append("autoplay")
    if muted:    attrs.append("muted")
    if loop:     attrs.append("loop")
    if controls: attrs.append("controls")
    attrs.extend([
        "playsinline",
        'preload="auto"',
        "disablepictureinpicture",
        'controlslist="nodownload noplaybackrate nofullscreen"',
    ])
    attr_str = " ".join(attrs)

    html_code = f"""
<div class="lowflicker-wrap">
  <video id="{vid_id}" class="lowflicker-video" {attr_str}
         style="width:100%;height:100%;object-fit:cover;background:#000;">
    <source src="data:video/mp4;base64,{b64}" type="video/mp4">
  </video>
</div>
<script>
(function(){{
  const v = document.getElementById("{vid_id}");
  if(!v) return;
  v.addEventListener('loadeddata', function(){{
    requestAnimationFrame(()=>{{ v.style.opacity = '1'; }});
  }});
  const tryPlay = () => v.play().catch(()=>{{ }});
  if (v.autoplay) {{
    if (v.readyState >= 2) tryPlay(); else v.addEventListener('canplay', tryPlay, {{once:true}});
  }}
}})();
</script>
"""
    components.html(html_code, height=iframe_h, scrolling=False)

# =============================
# メディア描画（文字列/辞書）
# =============================
def render_media(spec: Union[str, Dict[str, Any]]):
    if not spec:
        return
    if isinstance(spec, str):
        p = ensure_asset(spec)
        if str(p).lower().endswith(".mp4"):
            render_video(str(p))
        else:
            st.image(p, use_container_width=True)
        return

    mtype = (spec.get("type") or "").lower()
    file  = spec.get("file")
    if not file:
        if isinstance(spec.get("video"), str): mtype, file = "video", spec["video"]
        elif isinstance(spec.get("image"), str): mtype, file = "image", spec["image"]
    if not file: return

    if mtype == "video" or str(file).lower().endswith(".mp4"):
        render_video(
            file,
            autoplay=bool(spec.get("autoplay", True)),
            muted=bool(spec.get("muted", True)),
            loop=bool(spec.get("loop", False)),
            controls=bool(spec.get("controls", False)),
        )
    else:
        st.image(ensure_asset(file), use_container_width=True)

def render_chapter_media(chapter: Dict[str, Any]):
    spec = chapter.get("media") or chapter.get("video") or chapter.get("image")
    render_media(spec)

def render_result_media(chapter: Dict[str, Any], result_data: Dict[str, Any]):
    spec = (
        result_data.get("result_media")
        or result_data.get("result_image")
        or chapter.get("choice_media")
        or chapter.get("choice_image")
        or chapter.get("video")
        or chapter.get("image")
    )
    render_media(spec)

# =============================
# ナビゲーション
# =============================
def go_next_chapter(next_key: str):
    st.session_state.update({
        "chapter": str(next_key),
        "selected": None,
        "show_result": False,
        "lp_updated": False,
    })

def choose_index(i: int):
    st.session_state.update({"selected": i, "show_result": True, "lp_updated": False})

def start_game():
    st.session_state.update({"chapter": "1", "lp": 0, "lp_updated": False})

# =============================
# メイン
# =============================
def main():
    init_session()

    # --- Start 画面（JP固定） ---
    if st.session_state.chapter == "start":
        story = load_story()
        st.markdown("　　　")
        st.session_state.device_profile = st.selectbox(
            "\n\nデバイス",
            list(DEVICE_PROFILES.keys()),
            index=list(DEVICE_PROFILES.keys()).index(
                st.session_state.get("device_profile", "Standard Phone")
            ),
            help="端末に合わせて動画枠の挙動を選べます",
        )
        inject_device_css()

        # スタート画面
        st.image("assets/img_start.png", use_container_width=True)
        st.markdown("##### 無人島からの脱出 ヤドカリ島編")
        st.button("▶ ゲームを始める", on_click=start_game)
        render_text(story.get("intro_text", ""))
        return

    # --- ストーリー読込 ---
    story = load_story()

    # ★ 任意章クリア（JSONの clear_chapter が優先／無ければデフォルト"100"）
    clear_key = str(story.get("clear_chapter", GAME_CLEAR_CHAPTER_DEFAULT))
    if str(st.session_state.chapter) == clear_key:

        # 一度だけログ送信するためのフラグを用意
        if "clear_logged" not in st.session_state:
            st.session_state.clear_logged = False

        st.image("assets/img_gameclear.png", use_container_width=True)
        st.markdown(f"🏝️ サバイバル点: {st.session_state.lp} 点")

        rank, msg = calc_rank(int(st.session_state.lp))

        # ★ 初回だけログ送信
        if not st.session_state.clear_logged:
            log_clear_to_sheets(st.session_state.lp, rank, msg)
            st.session_state.clear_logged = True

        st.markdown(f"🏆 ランク：**{rank}**")
        st.markdown(f"📝 {msg}")

        if st.button("🔙 タイトルへ戻る"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        return

    # Chapter 取得
    chapter = story["chapters"].get(st.session_state.chapter)
    if not chapter:
        st.error("章データが見つかりません")
        return



    # ------ 結果表示（選択後） ------
    if st.session_state.show_result and st.session_state.selected is not None:
        choice = chapter["choices"][st.session_state.selected]
        result_data = choice["result"]

        if not st.session_state.lp_updated:
            delta = result_data.get("score", result_data.get("lp", 0))  # 後方互換
            st.session_state.lp = min(100, st.session_state.lp + delta)
            st.session_state.lp_updated = True

        render_result_media(chapter, result_data)
        # st.markdown(f"🏝️ サバイバル点: {st.session_state.lp} 点")

        render_text(result_data.get("text", ""))

        if choice.get("correct", False):
            st.button(
                "▶ 次へ",
                on_click=go_next_chapter,
                args=(str(result_data.get("next", "end")),),
            )
        else:
            st.button(
                "▶ もう一度選ぶ",
                on_click=lambda: st.session_state.update(
                    {"show_result": False, "selected": None, "lp_updated": False}
                ),
            )
        return

    # ------ 通常の章表示：メディア → テキスト → 選択肢 ------
    render_chapter_media(chapter)
    # st.markdown(f"🏝️ サバイバル点: {st.session_state.lp} 点")

    render_text(chapter.get("text", ""))

    # 選択肢が無い章は next へ「次へ」ボタン。それも無ければ後方互換でクリア
    choices = chapter.get("choices") or []
    if not choices:
        next_key = chapter.get("next")
        if next_key:
            st.button("▶ 次へ", on_click=go_next_chapter, args=(str(next_key),))
            return
        else:
            st.markdown("🎉 ゲームクリア！ 任務完了")
            clear_img = ensure_asset(CLEAR_IMAGE)
            # if clear_img.exists():
            #     st.image(str(clear_img), use_container_width=True)
            # else:
            #     st.balloons()
            if st.button("🔙 タイトルへ戻る"):
                for k in list(st.session_state.keys()):
                    del st.session_state[k]
                st.rerun()
            return

    # -------- 選択肢ボタン（縦並び・JSONの label をそのまま） --------
    for i, c in enumerate(choices):
        label = c.get("label") or personalize(c.get("text", "?"))
        st.button(label, key=f"choice_{i}", on_click=choose_index, args=(i,))

if __name__ == "__main__":
    main()
