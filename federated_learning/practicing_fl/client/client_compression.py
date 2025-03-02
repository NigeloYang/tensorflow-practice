# -*- coding: utf-8 -*-
# Time    : 2024/5/15
# By      : Yang

import torch
from model.models import LeNet,CNNMnist


class ClientCom(object):
    def __init__(self, args, train_dataset, id=-1):
        self.args = args
        self.local_model = CNNMnist().to(args.device)
        # self.local_model = LeNet().to(args.device)
        
        self.client_id = id
        
        self.train_dataset = train_dataset
        
        all_range = list(range(len(self.train_dataset)))
        data_len = int(len(self.train_dataset) / args.client_nums)
        train_indices = all_range[id * data_len: (id + 1) * data_len]
        
        self.train_loader = torch.utils.data.DataLoader(self.train_dataset, batch_size=args.batch_size,
                                                        sampler=torch.utils.data.sampler.SubsetRandomSampler(
                                                            train_indices))
    
    def local_train(self, global_model, c_id):
        
        for name, param in global_model.state_dict().items():
            self.local_model.state_dict()[name].copy_(param.clone())
        
        # print("\nlocal model train ... ... ")
        # for name, layer in self.local_model.named_parameters():
        #     print(name, "->", layer.size())
        
        optimizer = torch.optim.SGD(self.local_model.parameters(), lr=self.args.learn_rate, momentum=self.args.momentum)
        
        self.local_model.train()
        correct = 0
        dataset_size = 0
        for e in range(self.args.local_epochs):
            for batch_id, (data, target) in enumerate(self.train_loader):
                # for name, layer in self.local_model.named_parameters():
                #     print(name, '->', torch.mean(self.local_model.state_dict()[name].data))
                
                data = data.to(self.args.device)
                target = target.to(self.args.device)
                dataset_size += data.size()[0]
                
                optimizer.zero_grad()
                output = self.local_model(data)
                pred = output.data.max(1)[1]  # get the index of the max log-probability
                correct += pred.eq(target.data.view_as(pred)).cpu().sum().item()
                
                loss = torch.nn.functional.cross_entropy(output, target)
                loss.backward()
                optimizer.step()
            
            acc = 100.0 * (float(correct) / float(dataset_size))
            print("Client {:>2} | Local Train Epoch {:>3} Done. | Acc: {:>4.3f}".format(c_id, e, acc))
        
        diff = dict()
        for name, data in self.local_model.state_dict().items():
            diff[name] = (data - global_model.state_dict()[name])

        # print("local_model.state_dict()- global_model.state_dict()")
        # for name, layer in diff.items():
        #     print(name, '->', layer.size())
        
        # 按变化率从小到大排序
        diff = sorted(diff.items(), key=lambda item: abs(torch.mean(item[1].float())), reverse=True)
        # print("sort(diff)")
        # for name, layer in diff:
        #     print(name, '->', layer.size())

        sum1, sum2 = 0, 0
        for id, (name, data) in enumerate(diff):
            if id < 304:
                sum1 += torch.prod(torch.tensor(data.size()))
            else:
                sum2 += torch.prod(torch.tensor(data.size()))
                
        # 返回变化率最大的层
        ret_size = int(self.args.compress_rate * len(diff))
        # print('ret_size: ', ret_size)
        # diff_res = dict(diff[:ret_size])
        # print('dict(diff[:ret_size])')
        # for name, layer in diff_res.items():
        #     print(name, '->', layer.size())
        # print('*'*50)
        
        return dict(diff[:ret_size])
