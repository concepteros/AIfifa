const { worldCupData } = require("../../utils/worldcup-data");
const { teamLabel } = require("../../utils/helpers");

const STORAGE_KEY = "checkfifa_votes";
const CURRENT_KEY = "checkfifa_current_vote";

function readVotes() {
  return wx.getStorageSync(STORAGE_KEY) || {};
}

function writeVotes(votes) {
  wx.setStorageSync(STORAGE_KEY, votes);
}

Page({
  data: {
    teams: [],
    teamNames: [],
    selectedIndex: 0,
    selectedLabel: "",
    currentVote: "",
    currentVoteLabel: "尚未提交",
    totalVotes: 0,
    results: []
  },

  onLoad() {
    const teams = [...worldCupData.teams].sort((a, b) => a.name.localeCompare(b.name));
    const teamNames = teams.map(teamLabel);
    const currentVote = wx.getStorageSync(CURRENT_KEY) || "";
    const selectedIndex = Math.max(0, teams.findIndex((team) => team.code === currentVote));
    this.setData({
      teams,
      teamNames,
      selectedIndex,
      selectedLabel: teamNames[selectedIndex] || teamNames[0],
      currentVote
    });
    this.renderResults();
  },

  onPickTeam(event) {
    const selectedIndex = Number(event.detail.value);
    this.setData({
      selectedIndex,
      selectedLabel: this.data.teamNames[selectedIndex]
    });
  },

  submitVote() {
    const selected = this.data.teams[this.data.selectedIndex];
    if (!selected) return;
    const votes = readVotes();
    if (this.data.currentVote && votes[this.data.currentVote]) {
      votes[this.data.currentVote] = Math.max(0, votes[this.data.currentVote] - 1);
    }
    votes[selected.code] = (votes[selected.code] || 0) + 1;
    writeVotes(votes);
    wx.setStorageSync(CURRENT_KEY, selected.code);
    this.setData({ currentVote: selected.code });
    this.renderResults();
    wx.showToast({ title: "预测已记录", icon: "success" });
  },

  renderResults() {
    const votes = readVotes();
    const totalVotes = Object.values(votes).reduce((sum, value) => sum + Number(value || 0), 0);
    const results = worldCupData.teams
      .map((team) => {
        const count = Number(votes[team.code] || 0);
        const pct = totalVotes ? (count / totalVotes) * 100 : 0;
        return {
          code: team.code,
          label: teamLabel(team),
          votes: count,
          percentText: `${pct.toFixed(1)}%`
        };
      })
      .filter((item) => item.votes > 0)
      .sort((a, b) => b.votes - a.votes);
    const currentTeam = worldCupData.teams.find((team) => team.code === (wx.getStorageSync(CURRENT_KEY) || ""));
    this.setData({
      totalVotes,
      results,
      currentVoteLabel: currentTeam ? teamLabel(currentTeam) : "尚未提交"
    });
  }
});
