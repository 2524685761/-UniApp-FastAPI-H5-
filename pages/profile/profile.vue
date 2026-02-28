<template>
  <view class="profile-page">
    <view class="hero">
      <view class="hero-top">
        <view>
          <text class="title">👤 我的</text>
          <text class="hero-subtitle">本周练习总览</text>
        </view>
        <view class="header-actions" @click="goSettings">
          <text class="action-text">⚙️</text>
        </view>
      </view>
      <view class="hero-badges">
        <text class="hero-badge">连续学习 {{ stats.learning_days || 0 }} 天</text>
        <text class="hero-badge soft">平均分 {{ stats.avg_score || 0 }}</text>
      </view>
    </view>

    <view class="card profile-card">
      <view class="avatar">学</view>
      <view class="profile-meta">
        <text class="name">学习者 User {{ currentUserId }}</text>
        <text class="level">🏷️ {{ userLevel }} {{ levelEmoji }}</text>
      </view>
    </view>

    <view class="card switch-card">
      <text class="switch-label">测试用户</text>
      <view class="switch-controls">
        <button class="btn" @click="changeUserId(-1)">-</button>
        <text class="switch-value">User {{ currentUserId }}</text>
        <button class="btn" @click="changeUserId(1)">+</button>
      </view>
    </view>

    <view class="card stats-card">
      <view class="stat-item accent-1">
        <text class="stat-value">{{ stats.learning_days }}</text>
        <text class="stat-label">学习天数</text>
      </view>
      <view class="stat-item accent-2">
        <text class="stat-value">{{ stats.avg_score }}</text>
        <text class="stat-label">平均得分</text>
      </view>
      <view class="stat-item accent-3">
        <text class="stat-value">{{ stats.badges }}</text>
        <text class="stat-label">徽章</text>
      </view>
    </view>

    <view class="card records-card">
      <text class="section-title">📘 最近练习</text>
      <view v-if="recentRecords.length === 0" class="empty">暂无记录</view>
      <view v-else>
        <view class="record-item" v-for="item in recentRecords" :key="item.id">
          <text class="record-word">{{ item.word_text || '-' }}</text>
          <text class="record-meta">{{ item.score }} 分 · {{ item.emotion_label }}</text>
        </view>
      </view>
    </view>

    <view class="card mood-card">
      <text class="section-title">📊 情绪周报</text>
      <view class="bars">
        <view class="grid-line line-1"></view>
        <view class="grid-line line-2"></view>
        <view class="grid-line line-3"></view>
        <view class="bar-item" v-for="(day, index) in moodData" :key="index">
          <view class="bar-track">
            <view class="bar" :style="{ height: day.value + '%', background: day.color || '#52c41a' }"></view>
          </view>
          <text class="bar-day">{{ day.day }}</text>
        </view>
      </view>
      <text class="advice">{{ advice }}</text>
    </view>

    <view class="card menu-card">
      <view class="menu-item" @click="goVocabBook">
        <text class="menu-text">📒 我的生词本</text>
        <text class="menu-right">{{ vocabCount > 0 ? vocabCount : '' }} ></text>
      </view>
      <view class="menu-item" @click="goSettings">
        <text class="menu-text">⚙️ 设置</text>
        <text class="menu-right">></text>
      </view>
      <view class="menu-item" @click="goAbout">
        <text class="menu-text">ℹ️ 关于</text>
        <text class="menu-right">v1.0.0 ></text>
      </view>
    </view>

    <view class="custom-tabbar">
      <view class="tabbar-item" @click="switchToIndex">
        <text class="tabbar-icon">📚</text>
        <text class="tabbar-text">学习</text>
      </view>
      <view class="tabbar-item" @click="switchToChat">
        <text class="tabbar-icon">🤖</text>
        <text class="tabbar-text">AI聊天</text>
      </view>
      <view class="tabbar-item active" @click="switchToProfile">
        <text class="tabbar-icon">👤</text>
        <text class="tabbar-text">我的</text>
      </view>
    </view>
  </view>
</template>

<script>
import { fetchStats, fetchMoodWeekly, fetchRecords, getUserId, setUserId } from '@/utils/api.js'

export default {
  data() {
    return {
      userLevel: 'L1 入门',
      levelEmoji: '📘',
      currentUserId: 1,
      stats: { learning_days: 0, avg_score: 0, badges: 0 },
      recentRecords: [],
      moodData: [],
      advice: '先去练习几次，系统会自动生成本周建议。',
      vocabCount: 0
    }
  },
  onShow() {
    this.currentUserId = getUserId()
    this.loadStats()
    this.loadMood()
    this.loadRecords()
    this.loadVocabCount()
  },
  methods: {
    switchToIndex() {
      uni.switchTab({ url: '/pages/index/index' })
    },
    switchToChat() {
      uni.switchTab({ url: '/pages/chat/chat' })
    },
    switchToProfile() {},
    goVocabBook() {
      uni.navigateTo({ url: '/pages/vocabbook/vocabbook' })
    },
    goSettings() {
      uni.navigateTo({ url: '/pages/settings/settings' })
    },
    goAbout() {
      uni.showModal({
        title: '关于情感伴学系统',
        content: '这是一个面向普通话学习的情感伴学系统。',
        showCancel: false,
        confirmText: '知道了'
      })
    },
    changeUserId(delta) {
      const next = Math.max(1, Number(this.currentUserId || 1) + Number(delta || 0))
      this.currentUserId = next
      setUserId(next)
      this.loadStats()
      this.loadMood()
      this.loadRecords()
    },
    loadVocabCount() {
      const vocabBook = uni.getStorageSync('vocab_book') || []
      this.vocabCount = vocabBook.length
    },
    async loadStats() {
      try {
        const data = await fetchStats()
        if (data) {
          this.stats = data
          const avg = Number(this.stats.avg_score || 0)
          if (avg >= 85) {
            this.userLevel = 'L3 熟练'
            this.levelEmoji = '🏅'
          } else if (avg >= 70) {
            this.userLevel = 'L2 进阶'
            this.levelEmoji = '🌟'
          } else {
            this.userLevel = 'L1 入门'
            this.levelEmoji = '📘'
          }
        }
      } catch (err) {
        console.warn('加载统计失败:', err.message)
      }
    },
    async loadMood() {
      try {
        const data = await fetchMoodWeekly()
        if (Array.isArray(data)) {
          this.moodData = data.map((d) => ({
            ...d,
            emotionType: this.getEmotionType(d.emotion)
          }))
          this.advice = this.buildAdviceFromMood(data)
        }
      } catch (err) {
        console.warn('加载情绪周报失败:', err.message)
        this.moodData = [
          { day: '周一', value: 60, emotion: '平静', color: '#52c41a' },
          { day: '周二', value: 80, emotion: '积极', color: '#409EFF' },
          { day: '周三', value: 45, emotion: '困惑', color: '#fa8c16' },
          { day: '周四', value: 70, emotion: '平静', color: '#52c41a' },
          { day: '周五', value: 90, emotion: '积极', color: '#409EFF' },
          { day: '周六', value: 0, emotion: '无数据', color: '#d9d9d9' },
          { day: '周日', value: 0, emotion: '无数据', color: '#d9d9d9' }
        ]
      }
    },
    async loadRecords() {
      try {
        const data = await fetchRecords(8)
        this.recentRecords = Array.isArray(data) ? data : []
      } catch (err) {
        console.warn('加载记录失败:', err.message)
        this.recentRecords = []
      }
    },
    getEmotionType(emotion) {
      const map = {
        '积极': 'happy',
        '平静': 'normal',
        '困惑': 'confused',
        '挫败': 'frustrated',
        '无数据': 'none'
      }
      return map[emotion] || 'normal'
    },
    buildAdviceFromMood(days) {
      if (!Array.isArray(days) || !days.length) return '先去练习几次，系统会自动生成本周建议。'

      const emoCount = { 积极: 0, 平静: 0, 困惑: 0, 挫败: 0, 无数据: 0 }
      days.forEach((d) => {
        emoCount[d.emotion] = (emoCount[d.emotion] || 0) + 1
      })

      if ((emoCount.挫败 || 0) >= 2) return '这周出现多次挫败，建议先回到简单词练习，慢一点更稳。'
      if ((emoCount.困惑 || 0) >= 2) return '这周困惑偏多，建议多用“再练一次”，先听示范再跟读。'
      if ((emoCount.积极 || 0) >= 3) return '这周状态很好，可以尝试更有挑战的词语。'
      return '整体状态不错，建议每天固定 5 分钟：听示范 -> 跟读 -> 再读一遍巩固。'
    }
  }
}
</script>

<style>
:root {
  --bg-top: #fff7ec;
  --bg-main: #f6f7fb;
  --text-main: #1f2937;
  --text-soft: #6b7280;
  --brand: #ff9f43;
  --brand-2: #e17055;
  --card-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.06);
}

.profile-page {
  min-height: 100vh;
  background: linear-gradient(180deg, var(--bg-top) 0%, var(--bg-main) 35%, var(--bg-main) 100%);
  padding: 24rpx 24rpx 160rpx;
  box-sizing: border-box;
}

.hero {
  background: linear-gradient(140deg, rgba(255, 159, 67, 0.15), rgba(225, 112, 85, 0.08));
  border: 1rpx solid rgba(255, 159, 67, 0.25);
  border-radius: 24rpx;
  padding: 20rpx 20rpx 16rpx;
  margin-bottom: 16rpx;
}

.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hero-subtitle {
  display: block;
  font-size: 22rpx;
  color: var(--text-soft);
  margin-top: 6rpx;
}

.hero-badges {
  margin-top: 14rpx;
  display: flex;
  gap: 10rpx;
}

.title {
  font-size: 40rpx;
  font-weight: 700;
  color: var(--text-main);
}

.hero-badge {
  font-size: 20rpx;
  color: #8a4b0f;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 999rpx;
  padding: 6rpx 14rpx;
}

.hero-badge.soft {
  color: #515f78;
}

.header-actions {
  background: #fff3e0;
  border-radius: 16rpx;
  padding: 12rpx 20rpx;
}

.action-text {
  color: #333;
  font-size: 26rpx;
}

.card {
  background: #fff;
  border-radius: 20rpx;
  padding: 20rpx;
  margin-bottom: 16rpx;
  box-shadow: var(--card-shadow);
}

.profile-card {
  display: flex;
  align-items: center;
}

.avatar {
  width: 88rpx;
  height: 88rpx;
  border-radius: 44rpx;
  background: linear-gradient(145deg, var(--brand), var(--brand-2));
  color: #fff;
  text-align: center;
  line-height: 88rpx;
  font-weight: 700;
  margin-right: 16rpx;
}

.profile-meta {
  display: flex;
  flex-direction: column;
}

.name {
  font-size: 30rpx;
  font-weight: 600;
  color: var(--text-main);
}

.level {
  font-size: 24rpx;
  color: var(--text-soft);
  margin-top: 6rpx;
}

.switch-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.switch-label {
  color: var(--text-soft);
}

.switch-controls {
  display: flex;
  align-items: center;
}

.switch-value {
  margin: 0 12rpx;
  font-size: 26rpx;
  color: var(--text-main);
}

.btn {
  width: 56rpx;
  height: 56rpx;
  line-height: 56rpx;
  padding: 0;
  border: none;
  border-radius: 28rpx;
  background: #fff3e0;
  color: #e17055;
}

.stats-card {
  display: flex;
  justify-content: space-between;
  gap: 12rpx;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 14rpx 8rpx;
  border-radius: 14rpx;
}

.stat-item.accent-1 {
  background: linear-gradient(160deg, rgba(64, 158, 255, 0.15), rgba(64, 158, 255, 0.04));
}

.stat-item.accent-2 {
  background: linear-gradient(160deg, rgba(255, 159, 67, 0.18), rgba(255, 159, 67, 0.05));
}

.stat-item.accent-3 {
  background: linear-gradient(160deg, rgba(82, 196, 26, 0.16), rgba(82, 196, 26, 0.04));
}

.stat-value {
  font-size: 34rpx;
  font-weight: 700;
  color: var(--text-main);
}

.stat-label {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: var(--text-soft);
}

.section-title {
  font-size: 30rpx;
  font-weight: 600;
  margin-bottom: 12rpx;
}

.empty {
  font-size: 24rpx;
  color: #999;
}

.record-item {
  display: flex;
  justify-content: space-between;
  padding: 12rpx 0;
  border-bottom: 1rpx solid #f0f0f0;
}

.record-item:last-child {
  border-bottom: none;
}

.record-meta {
  color: var(--text-soft);
  font-size: 24rpx;
}

.bars {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 220rpx;
  border-radius: 12rpx;
  padding: 8rpx 10rpx 0;
  background: linear-gradient(180deg, #fbfcff 0%, #ffffff 100%);
}

.grid-line {
  position: absolute;
  left: 8rpx;
  right: 8rpx;
  border-top: 1rpx dashed #e8ebf0;
}

.grid-line.line-1 {
  top: 48rpx;
}

.grid-line.line-2 {
  top: 98rpx;
}

.grid-line.line-3 {
  top: 148rpx;
}

.bar-item {
  z-index: 1;
  width: 13%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.bar-track {
  width: 24rpx;
  height: 180rpx;
  background: #f0f0f0;
  border-radius: 12rpx;
  position: relative;
  overflow: hidden;
}

.bar {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 12rpx;
  box-shadow: 0 4rpx 8rpx rgba(0, 0, 0, 0.12);
}

.bar-day {
  margin-top: 8rpx;
  font-size: 20rpx;
  color: #666;
}

.advice {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  color: #334155;
  line-height: 1.6;
  background: #fff7ec;
  border: 1rpx solid #ffe4bf;
  border-radius: 12rpx;
  padding: 12rpx;
}

.menu-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #f3f3f3;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-text,
.menu-right {
  font-size: 26rpx;
}

.menu-right {
  color: #888;
}

.custom-tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: 120rpx;
  background: #fff;
  border-top: 1rpx solid #eee;
  display: flex;
  align-items: center;
  z-index: 999;
  box-shadow: 0 -8rpx 20rpx rgba(0, 0, 0, 0.06);
  padding-bottom: constant(safe-area-inset-bottom);
  padding-bottom: env(safe-area-inset-bottom);
}

.tabbar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #666;
  gap: 2rpx;
}

.tabbar-icon {
  font-size: 40rpx;
}

.tabbar-text {
  font-size: 22rpx;
}

.tabbar-item.active .tabbar-text {
  color: var(--brand);
  font-weight: 600;
}
</style>
