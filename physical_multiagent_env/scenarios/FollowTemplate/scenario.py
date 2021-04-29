from physical_multiagent_env.envs.PhysicalEnv import PhysicalEnv
import pybullet as p 
import numpy as np 
import random 
from physical_multiagent_env.utils.maps import *

# from physical_multiagent_env.envs.PhysicalObjects import PhysicalObjects, Agent
# import pybullet as p 
# import numpy as np 
# import time 
# import pybullet_data 
# import gym 
from gym.spaces import Dict

class FollowTemplate(PhysicalEnv):
    def __init__(self, config={}):
        super().__init__(config)
        self.max_timestep = config.get("max_timestep", 10000)
        self.remove_candidates =[]
        self.terminal_agent_num = np.clip(config.get("terminal_agent_num", 10), 1, self.num_agents)
        self.directions = ["x+", "x-", "y+", "y-"] 
        self.follow_intensity = 1
        self.avoid_intensity = 1
        
        p.setTimeStep(config.get("pybullet_timestep", 0.01))
        self.phase = 6
        self.maps = [None, GridMap1(), GridMap2(), GridMap3(),None, None, GridMap6()]
        self.map = self.maps[self.phase]

        

    # Similar to the linear combination
    def set_phase(self, **kwargs):
        self.follow_intensity = kwargs.get("follow_intensity", 0.5)
        self.avoid_intensity = kwargs.get("avoid_intensity", 0.5)
        self.phase = kwargs.get("phase", 6)
        self.map = self.maps[self.phase]
        self.num_obstacles = self.map.num_obstacles



    def reset(self):
        if self.objects:
            for object_type, object_list in self.objects.items():
                for obj in object_list:
                    obj.remove()
                object_list.clear()
        if 1<=self.phase<=6:
            for _ in range(self.num_targets):
                self.build_position("target", [t-i for t,i in zip(self.map.target_position, self.map.init_position)] , **self.config.get("target", None))
            for _ in range(self.num_agents):
                self.build_position("agent",  [a-i for a,i in zip(self.map.agent_position, self.map.init_position)], **self.config.get("agent", None))
            for r in range(self.map.width):
                for c in range(self.map.height):
                    if self.map.map1[r][c] == 1:
                        self.build_position("obstacle", [r-self.map.init_position[0], c-self.map.init_position[1] ,0], **self.config.get("obstacle", None))
            for obj in self.objects["obstacle"]:
                p.changeDynamics(obj.pid, -1, mass=100000)

        self.observation_space = Dict({
            i: agent.observation_space for i, agent in enumerate(self.objects['agent'])
        })
        self.action_space = Dict({
            i : agent.action_space for i, agent in enumerate(self.objects['agent'])    
        })
        self.done = {i:False for i in range(len(self.objects['agent']))}
        self.done['__all__'] = False
        self.timestep = 0

        self.objects['target'][0].move_kind = "x-"

        return {i : np.hstack([agent.position,
                               agent.velocity])
                for i, agent in enumerate(self.objects['agent'])}

    def step(self, agent_action):
        if self.phase ==1 :
            pass 
        elif self.phase ==2:
            pass 

        for agent, action in agent_action.items():
            self.objects['agent'][agent].take_action(action, bound=np.inf)        
        for target in self.objects['target']:
            if self.timestep%(87*4)==347:
                order = ["x-","y+", "x+", "y-"]
                target.move_kind = order[(order.index(target.move_kind)+1)%4]
            target.move(target.move_kind, bound=np.inf)

        p.stepSimulation()
        for object_type, object_list in self.objects.items():
            for obj in object_list:
                if obj.alive:
                    obj.update()
                    obj.decrease_velocity()
                    obj.clip_velocity()

        state ={agent : np.hstack([self.objects['agent'][agent].position,
                                   self.objects['agent'][agent].velocity])
                    for agent in agent_action.keys()}

        reward = self._reward(agent_action.keys())
        done = self._done(agent_action.keys())
        info = self._info()
        self.timestep +=1
        return state, reward, done, info

    def _reward(self, agents): 
        self.remove_candidates.clear()  
        reward = {a:0 for a  in agents}
        for a in agents:
            agent = self.objects['agent'][a]
            if p.getContactPoints(agent.pid):
                reward[a] -= 1 * self.avoid_intensity
                self.remove_candidates.append(a)
            for target in self.objects['target']:
                distance = agent.distance(target)
                if 0.4 < distance < 0.5:
                    reward[a] += 1/self.max_timestep * self.follow_intensity 
                # else:
                #     reward[a] += -1/self.max_timestep * self.follow_intensity 
        return reward 

    def _done(self, agents):
        for a in set(self.remove_candidates):
            self.done[a] = True 
            self.objects['agent'][a].remove()
            
        if (sum([v for v in self.done.values()]) >= self.terminal_agent_num):            
            self.done['__all__'] = True 
        if self.timestep > self.max_timestep:
            self.done['__all__'] = True 

        return self.done 
         
    def _info(self):
        return {}

import time
import json 
if __name__ == "__main__":
    with open("../../reinforcement_learning/FollowTemplate/version1.json") as f :
        config = json.load(f)

    config = config['env_config']
    config['connect'] = p.GUI

    env = FollowTemplate(config)
    
    for i in range(10):
        env.set_phase(phase=3)
        env.reset()
        
        for j in range(2000):
            alive_agents = []
            for index, agent in enumerate(env.objects['agent']):
                if agent.alive:
                    alive_agents.append(index)
            if j%30==0:
                action = np.random.randint(5)

            state, reward, done, info = env.step({i:action for i in alive_agents})
            time.sleep(0.01)