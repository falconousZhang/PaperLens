<template>
  <div class="home">
    <div class="glow glow-left" aria-hidden="true"></div>
    <div class="glow glow-right" aria-hidden="true"></div>

    <main class="hero">
      <div class="brand-mark" aria-hidden="true">PL</div>
      <p class="eyebrow">专注阅读 · 深入理解 · 持续积累</p>
      <h1>PaperLens</h1>
      <p class="subtitle">AI 驱动的个人论文阅读学习助手</p>

      <div class="actions" aria-label="账户入口">
        <router-link to="/login" class="action-btn primary">登录</router-link>
        <router-link to="/register" class="action-btn secondary">注册</router-link>
      </div>
    </main>
  </div>
</template>

<style scoped>
.home {
  position: relative;
  display: grid;
  min-height: 100vh;
  place-items: center;
  overflow: hidden;
  padding: 2rem;
  color: #17213b;
  background:
    linear-gradient(rgba(255, 255, 255, 0.72), rgba(247, 249, 253, 0.9)),
    radial-gradient(circle at top left, #e7eeff 0, transparent 42%),
    radial-gradient(circle at bottom right, #e9e4ff 0, transparent 40%),
    #f7f9fd;
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.glow {
  position: absolute;
  width: 24rem;
  height: 24rem;
  border-radius: 50%;
  filter: blur(1px);
  opacity: 0.45;
  pointer-events: none;
}

.glow-left {
  top: -12rem;
  left: -10rem;
  background: radial-gradient(circle, rgba(65, 91, 180, 0.22), transparent 68%);
}

.glow-right {
  right: -11rem;
  bottom: -13rem;
  background: radial-gradient(circle, rgba(110, 78, 173, 0.2), transparent 68%);
}

.hero {
  position: relative;
  z-index: 1;
  width: min(100%, 650px);
  padding: clamp(3.5rem, 8vw, 5.5rem) clamp(1.5rem, 7vw, 5rem);
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.88);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.68);
  box-shadow: 0 28px 80px rgba(36, 47, 82, 0.12);
  backdrop-filter: blur(18px);
}

.brand-mark {
  display: grid;
  width: 52px;
  height: 52px;
  margin: 0 auto 1.5rem;
  place-items: center;
  border-radius: 16px;
  color: #fff;
  background: linear-gradient(145deg, #171d3a, #3b4679);
  box-shadow: 0 12px 28px rgba(30, 40, 82, 0.24);
  font-size: 0.9rem;
  font-weight: 750;
  letter-spacing: 0.08em;
}

.eyebrow {
  margin: 0 0 0.9rem;
  color: #69728a;
  font-size: 0.8rem;
  font-weight: 650;
  letter-spacing: 0.16em;
}

h1 {
  margin: 0;
  color: #111936;
  font-size: clamp(3rem, 8vw, 5rem);
  font-weight: 760;
  letter-spacing: -0.055em;
  line-height: 1;
}

.subtitle {
  margin: 1.25rem 0 0;
  color: #69728a;
  font-size: clamp(1rem, 2.5vw, 1.2rem);
  line-height: 1.7;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 0.9rem;
  margin-top: 2rem;
}

.action-btn {
  display: inline-flex;
  min-width: 132px;
  min-height: 46px;
  align-items: center;
  justify-content: center;
  padding: 0.7rem 1.8rem;
  border: 1px solid transparent;
  border-radius: 12px;
  text-decoration: none;
  font-size: 0.98rem;
  font-weight: 650;
  transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
}

.action-btn:hover {
  transform: translateY(-2px);
}

.action-btn:focus-visible {
  outline: 3px solid rgba(67, 91, 174, 0.28);
  outline-offset: 3px;
}

.action-btn.primary {
  color: #fff;
  background: #171d3a;
  box-shadow: 0 10px 24px rgba(23, 29, 58, 0.22);
}

.action-btn.primary:hover {
  box-shadow: 0 14px 28px rgba(23, 29, 58, 0.28);
}

.action-btn.secondary {
  border-color: #d8ddea;
  color: #293352;
  background: rgba(255, 255, 255, 0.8);
}

.action-btn.secondary:hover {
  border-color: #adb6cf;
  box-shadow: 0 10px 24px rgba(45, 57, 94, 0.1);
}

@media (max-width: 560px) {
  .home {
    padding: 1rem;
  }

  .hero {
    border-radius: 22px;
  }

  .eyebrow {
    letter-spacing: 0.1em;
  }

  .actions {
    flex-direction: column;
  }

  .action-btn {
    width: 100%;
  }
}
</style>
