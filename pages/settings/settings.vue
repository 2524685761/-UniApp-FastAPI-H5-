<template>
	<view class="settings-page">
		<!-- 自定义顶部导航栏 -->
		<view class="custom-navbar">
			<view class="navbar-content">
				<view class="navbar-left" @click="goBack">
					<text class="back-icon">←</text>
				</view>
				<view class="navbar-center">
					<text class="navbar-title">⚙️ 设置</text>
				</view>
				<view class="navbar-right"></view>
			</view>
		</view>

		<!-- 页面内容区 -->
		<view class="page-content">

		<!-- 后端地址设置 -->
		<view class="settings-card">
			<view class="card-header">
				<text class="card-icon">🔗</text>
				<text class="card-title">后端服务器</text>
			</view>
			<view class="current-user-tip">当前用户：User {{ userIdInput }}</view>
			
			<view class="input-group">
				<text class="input-label">后端地址</text>
				<view class="input-wrapper">
					<input 
						class="input-field" 
						v-model="apiBaseUrl" 
						placeholder="例如：192.168.1.8:8000" 
						placeholder-class="input-placeholder"
					/>
				</view>
			</view>
			
			<view class="input-group">
				<text class="input-label">User ID</text>
				<view class="input-wrapper">
					<input 
						class="input-field" 
						v-model="userIdInput"
						type="number"
						placeholder="例如: 1"
						placeholder-class="input-placeholder"
					/>
				</view>
				<button class="btn secondary single-btn" @click="saveUserId">
					<text class="btn-icon">👤</text>
					<text>保存用户</text>
				</button>
			</view>
			
			<view class="button-group">
				<button class="btn primary" @click="saveApiUrl">
					<text class="btn-icon">💾</text>
					<text>保存</text>
				</button>
				<button class="btn secondary" @click="testApi">
					<text class="btn-icon">🔍</text>
					<text>测试连接</text>
				</button>
			</view>
			
			<view class="status-box" :class="statusType">
				<text class="status-icon">{{ statusIcon }}</text>
				<text class="status-text">{{ apiHint }}</text>
			</view>
		</view>

		<!-- 使用提示 -->
		<view class="tips-card">
			<view class="card-header">
				<text class="card-icon">💡</text>
				<text class="card-title">使用提示</text>
			</view>
			
			<view class="tips-list">
				<view class="tip-item">
					<text class="tip-number">1</text>
					<text class="tip-text">手机/真机不要填 127.0.0.1，请填电脑局域网 IP</text>
				</view>
				<view class="tip-item">
					<text class="tip-number">2</text>
					<text class="tip-text">浏览器录音需麦克风权限，部分环境需要 HTTPS</text>
				</view>
				<view class="tip-item">
					<text class="tip-number">3</text>
					<text class="tip-text">后端默认端口 8000（可在启动命令中修改）</text>
				</view>
			</view>
		</view>

		<!-- 其他设置 -->
		<view class="settings-card">
			<view class="card-header">
				<text class="card-icon">🎛️</text>
				<text class="card-title">其他设置</text>
			</view>
			
			<view class="menu-item" @click="clearCache">
				<view class="menu-left">
					<text class="menu-icon">🗑️</text>
					<text class="menu-text">清除缓存</text>
				</view>
				<text class="menu-arrow">›</text>
			</view>
			
			<view class="menu-item" @click="resetStars">
				<view class="menu-left">
					<text class="menu-icon">⭐</text>
					<text class="menu-text">重置星星数</text>
				</view>
				<text class="menu-arrow">›</text>
			</view>
		</view>
		</view>
	</view>
</template>

<script>
	import { getBaseURL, setBaseURL, buildURL, getUserId, setUserId } from '../../utils/api.js'
	
	export default {
		data() {
			return {
				apiBaseUrl: '',
				userIdInput: '1',
				apiHint: '建议：手机访问时填电脑IP，如 192.168.x.x:8000',
				statusType: 'info',
				statusIcon: 'ℹ️'
			}
		},
		onShow() {
			this.apiBaseUrl = getBaseURL().replace(/^https?:\/\//i, '')
			this.userIdInput = String(getUserId())
		},
		methods: {
			goBack() {
				uni.navigateBack()
			},
			saveApiUrl() {
				const u = setBaseURL(this.apiBaseUrl)
				this.apiBaseUrl = u.replace(/^https?:\/\//i, '')
				uni.showToast({ title: '已保存', icon: 'success' })
			},
			saveUserId() {
				const saved = setUserId(this.userIdInput)
				this.userIdInput = String(saved)
				uni.showToast({ title: `User ${saved}`, icon: 'success' })
			},
			testApi() {
				this.saveApiUrl()
				uni.showLoading({ title: '测试中...' })
				this.statusType = 'loading'
				this.statusIcon = '⏳'
				this.apiHint = '正在测试连接...'
				
				uni.request({
					url: buildURL('/courses'),
					timeout: 4000,
					success: (res) => {
						if (res.statusCode === 200) {
							this.statusType = 'success'
							this.statusIcon = '✅'
							this.apiHint = `连接成功！已获取 ${Array.isArray(res.data) ? res.data.length : 0} 个课程`
							uni.showToast({ title: '连接成功', icon: 'success' })
						} else {
							this.statusType = 'error'
							this.statusIcon = '❌'
							this.apiHint = `连接失败：HTTP ${res.statusCode}`
							uni.showToast({ title: '连接失败', icon: 'none' })
						}
					},
					fail: (err) => {
						this.statusType = 'error'
						this.statusIcon = '❌'
						this.apiHint = `连接失败：${err.errMsg || '请检查IP/端口/同网段'}`
						uni.showToast({ title: '连接失败', icon: 'none' })
					},
					complete: () => uni.hideLoading()
				})
			},
			clearCache() {
				uni.showModal({
					title: '清除缓存',
					content: '确定要清除本地缓存吗？这不会影响你的学习记录。',
					success: (res) => {
						if (res.confirm) {
							uni.clearStorageSync()
							uni.showToast({ title: '缓存已清除', icon: 'success' })
						}
					}
				})
			},
			resetStars() {
				uni.showModal({
					title: '重置星星',
					content: '确定要重置星星数为0吗？',
					success: (res) => {
						if (res.confirm) {
							uni.setStorageSync('user_stars', 0)
							uni.showToast({ title: '已重置', icon: 'success' })
						}
					}
				})
			}
		}
	}
</script>

<style>
	/* ========== 页面容器 ========== */
	.settings-page {
		min-height: 100vh;
		background: linear-gradient(180deg, #F8F9FA 0%, #ECEFF1 100%);
	}

	/* ========== 自定义顶部导航栏 ========== */
	.custom-navbar {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		z-index: 999;
		background: linear-gradient(145deg, #607D8B, #455A64);
		padding-top: constant(safe-area-inset-top);
		padding-top: env(safe-area-inset-top);
	}
	
	.navbar-content {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 24rpx 32rpx;
	}
	
	.navbar-left {
		width: 72rpx;
		height: 72rpx;
		background: rgba(255, 255, 255, 0.2);
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
	}
	
	.back-icon {
		font-size: 36rpx;
		color: #FFF;
	}
	
	.navbar-center {
		flex: 1;
		text-align: center;
	}
	
	.navbar-title {
		font-size: 36rpx;
		font-weight: bold;
		color: #FFF;
	}
	
	.navbar-right {
		width: 72rpx;
	}

	/* ========== 页面内容区 ========== */
	.page-content {
		padding: 32rpx;
		padding-top: calc(constant(safe-area-inset-top) + 120rpx);
		padding-top: calc(env(safe-area-inset-top) + 120rpx);
		padding-bottom: 60rpx;
	}

	/* ========== 设置卡片 ========== */
	.settings-card, .tips-card {
		background: #FFF;
		border-radius: 28rpx;
		padding: 28rpx;
		margin-bottom: 24rpx;
		box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.06);
	}
	
	.card-header {
		display: flex;
		align-items: center;
		gap: 12rpx;
		margin-bottom: 24rpx;
	}
	
	.card-icon {
		font-size: 32rpx;
	}
	
	.card-title {
		font-size: 30rpx;
		font-weight: bold;
		color: #2D3436;
	}

	.current-user-tip {
		font-size: 24rpx;
		color: #607D8B;
		margin-bottom: 16rpx;
	}

	/* ========== 输入框 ========== */
	.input-group {
		margin-bottom: 24rpx;
	}
	
	.input-label {
		font-size: 26rpx;
		color: #636E72;
		display: block;
		margin-bottom: 12rpx;
	}
	
	.input-wrapper {
		display: flex;
		align-items: center;
		background: #F8F9FA;
		border-radius: 20rpx;
		border: 2rpx solid #E0E0E0;
		overflow: hidden;
	}
	
	.input-field {
		flex: 1;
		padding: 20rpx;
		font-size: 28rpx;
		color: #2D3436;
	}
	
	.input-placeholder {
		color: #B2BEC3;
	}

	/* ========== 按钮组 ========== */
	.button-group {
		display: flex;
		gap: 16rpx;
		margin-bottom: 20rpx;
	}
	
	.btn {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8rpx;
		height: 88rpx;
		border-radius: 44rpx;
		font-size: 28rpx;
		font-weight: 600;
		border: none;
		transition: all 0.2s;
	}
	
	.btn:active {
		transform: scale(0.98);
	}
	
	.btn.primary {
		background: linear-gradient(145deg, #FF9F43, #E17055);
		color: #FFF;
		box-shadow: 0 6rpx 0 #C44A34;
	}
	
	.btn.secondary {
		background: #E8F4FD;
		color: #3498DB;
		border: 2rpx solid #3498DB;
	}

	.single-btn {
		margin-top: 14rpx;
	}
	
	.btn-icon {
		font-size: 28rpx;
	}

	/* ========== 状态提示 ========== */
	.status-box {
		display: flex;
		align-items: flex-start;
		gap: 12rpx;
		padding: 16rpx 20rpx;
		border-radius: 16rpx;
		margin-top: 16rpx;
	}
	
	.status-box.info {
		background: #E3F2FD;
	}
	
	.status-box.success {
		background: #E8F5E9;
	}
	
	.status-box.error {
		background: #FFEBEE;
	}
	
	.status-box.loading {
		background: #FFF8E1;
	}
	
	.status-icon {
		font-size: 28rpx;
	}
	
	.status-text {
		flex: 1;
		font-size: 26rpx;
		color: #636E72;
		line-height: 1.5;
	}

	/* ========== 提示列表 ========== */
	.tips-list {
		display: flex;
		flex-direction: column;
		gap: 16rpx;
	}
	
	.tip-item {
		display: flex;
		align-items: flex-start;
		gap: 16rpx;
	}
	
	.tip-number {
		width: 40rpx;
		height: 40rpx;
		background: linear-gradient(145deg, #FF9F43, #E17055);
		color: #FFF;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 24rpx;
		font-weight: bold;
		flex-shrink: 0;
	}
	
	.tip-text {
		flex: 1;
		font-size: 26rpx;
		color: #636E72;
		line-height: 1.6;
	}

	/* ========== 菜单项 ========== */
	.menu-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 24rpx 0;
		border-bottom: 2rpx solid #F0F0F0;
	}
	
	.menu-item:last-child {
		border-bottom: none;
	}
	
	.menu-left {
		display: flex;
		align-items: center;
		gap: 16rpx;
	}
	
	.menu-icon {
		font-size: 32rpx;
	}
	
	.menu-text {
		font-size: 28rpx;
		color: #2D3436;
	}
	
	.menu-arrow {
		font-size: 32rpx;
		color: #B2BEC3;
	}
</style>
